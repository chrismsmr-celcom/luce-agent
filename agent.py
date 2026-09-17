import os
import json
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
from agentguard import AgentGuard, SecurityException

load_dotenv()

# ==============================================================================
# 1. INITIALISATION DE CERBERE
# ==============================================================================
guard = AgentGuard(
    collector_url=os.getenv("AGENTGUARD_COLLECTOR_URL", "https://app.cerbereag.site"),
    api_key=os.getenv("AGENTGUARD_API_KEY"),
    max_budget=10.0,
    block_on_high=True
)

# ==============================================================================
# 2. INITIALISATION DE DEEPSEEK
# ==============================================================================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ==============================================================================
# 3. INITIALISATION DE COMPOSIO (Pattern officiel avec sécurité Render)
# ==============================================================================
composio_session = None
composio_error = None

try:
    from composio import Composio
    
    api_key = os.getenv("COMPOSIO_API_KEY")
    user_id = os.getenv("COMPOSIO_USER_ID", "luce_default_user")
    
    if api_key:
        composio_client = Composio(api_key=api_key)
        
        # CRUCIAL : wait_for_connections=False pour éviter le blocage sur Render
        composio_session = composio_client.create(
            user_id=user_id,
            toolkits=[
                "gmail",
                "googledrive",
                "googlecalendar",
            ],
            manage_connections={
                "wait_for_connections": False, 
            },
        )
        print("✅ Session Composio initialisée avec succès.")
    else:
        composio_error = "COMPOSIO_API_KEY manquante dans les variables d'environnement."
        
except Exception as e:
    composio_error = f"Erreur Composio (clé invalide, révoquée ou HTTP 410) : {str(e)}"
    print(f"⚠️ COMPOSIO WARNING: {composio_error}")

# ==============================================================================
# 4. OUTILS MÉTIER (Avec fallback gracieux)
# ==============================================================================

@guard.guard_tool_call
def read_emails(query: str = "inbox", max_results: int = 10) -> Dict[str, Any]:
    """Lit les emails récents via Gmail."""
    if composio_session is None:
        return {"status": "error", "message": f"Composio indisponible : {composio_error}"}
    try:
        response = composio_session.execute_action(
            app="gmail",
            action="GMAIL_FETCH_EMAILS",
            params={"query": query, "maxResults": max_results}
        )
        return {"status": "success", "emails": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Envoie un email via Gmail."""
    if composio_session is None:
        return {"status": "error", "message": f"Composio indisponible : {composio_error}"}
    try:
        response = composio_session.execute_action(
            app="gmail",
            action="GMAIL_SEND_EMAIL",
            params={"to": to, "subject": subject, "body": body}
        )
        return {"status": "sent", "message_id": response.get("id", "mock_id")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def check_calendar(date: str = "today") -> Dict[str, Any]:
    """Vérifie le calendrier."""
    if composio_session is None:
        return {"status": "error", "message": f"Composio indisponible : {composio_error}"}
    try:
        response = composio_session.execute_action(
            app="googlecalendar",
            action="GOOGLECALENDAR_GET_EVENTS",
            params={"date": date}
        )
        return {"status": "success", "events": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def list_drive_files(query: str = "") -> Dict[str, Any]:
    """Liste les fichiers Drive."""
    if composio_session is None:
        return {"status": "error", "message": f"Composio indisponible : {composio_error}"}
    try:
        response = composio_session.execute_action(
            app="googledrive",
            action="GOOGLEDRIVE_LIST_FILES",
            params={"query": query}
        )
        return {"status": "success", "files": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================================================================
# 5. SYSTEM PROMPT DE LUCE
# ==============================================================================
LUCE_SYSTEM_PROMPT = """Tu es Luce, une assistante virtuelle professionnelle spécialisée dans la gestion administrative.

Tes responsabilités :
- Gérer les emails : lire, résumer, répondre
- Gérer le calendrier : vérifier disponibilités
- Gérer les documents : lister fichiers sur Drive
- Fournir des résumés et analyses

Style : Professionnel, efficace, proactif. Tu vas droit au but.
Tu es une assistante métier, pas un outil de sécurité.
"""

# ==============================================================================
# 6. CERVEAU DE LUCE
# ==============================================================================

@guard.guard_llm_call
def call_deepseek(messages: List[Dict[str, str]]) -> Any:
    """Appelle DeepSeek."""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.3,
        max_tokens=1000
    )
    return response

def luce_process_message(user_input: str, chat_history: List[Dict[str, str]]) -> tuple[str, str]:
    """Traite un message utilisateur."""
    messages = [{"role": "system", "content": LUCE_SYSTEM_PROMPT}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_input})
    
    try:
        response = call_deepseek(messages=messages)
        assistant_reply = response.choices[0].message.content
        
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ["envoyer", "envoie", "send", "transférer"]):
            tool_result = send_email(
                to="recipient@example.com", 
                subject="Message de Luce",
                body=assistant_reply[:500]
            )
            if tool_result["status"] == "sent":
                assistant_reply += f"\n\n✅ Email envoyé avec succès."
            else:
                assistant_reply += f"\n\n❌ Erreur : {tool_result['message']}"
        
        elif any(word in user_lower for word in ["email", "résumer", "inbox"]):
            tool_result = read_emails(query="inbox", max_results=5)
            if tool_result["status"] == "success":
                assistant_reply += f"\n\n📧 J'ai récupéré tes emails récents."
            else:
                assistant_reply += f"\n\n⚠️ Impossible de lire les emails : {tool_result['message']}"
        
        elif any(word in user_lower for word in ["calendrier", "rendez-vous", "agenda"]):
            tool_result = check_calendar(date="today")
            if tool_result["status"] == "success":
                assistant_reply += f"\n\n📅 J'ai vérifié ton calendrier."
            else:
                assistant_reply += f"\n\n⚠️ Impossible d'accéder au calendrier : {tool_result['message']}"
        
        elif any(word in user_lower for word in ["fichier", "document", "drive"]):
            tool_result = list_drive_files()
            if tool_result["status"] == "success":
                assistant_reply += f"\n\n📁 J'ai listé tes fichiers Drive."
            else:
                assistant_reply += f"\n\n⚠️ Impossible d'accéder à Drive : {tool_result['message']}"
        
        return assistant_reply, "ALLOWED"
    
    except SecurityException as e:
        return f"🛡️ Action bloquée par le système de sécurité : {str(e)}", "BLOCKED"
    
    except Exception as e:
        return f"❌ Erreur système : {str(e)}", "ERROR"
