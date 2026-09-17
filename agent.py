import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
from composio import ComposioToolSet, App, Action
from agentguard import AgentGuard, SecurityException

load_dotenv()

# ==============================================================================
# 1. INITIALISATION TRANSPARENTE DE CERBERE
# ==============================================================================
# Luce ne "sait pas" qu'elle est protégée. Cerbere est juste un middleware.
guard = AgentGuard(
    collector_url=os.getenv("AGENTGUARD_COLLECTOR_URL", "https://app.cerbereag.site"),
    api_key=os.getenv("AGENTGUARD_API_KEY"),
    max_budget=10.0,
    block_on_high=True
)

# ==============================================================================
# 2. INITIALISATION DE DEEPSEEK (LLM)
# ==============================================================================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ==============================================================================
# 3. INITIALISATION DE COMPOSIO (OUTILS MÉTIER)
# ==============================================================================
composio_toolset = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY"))

# Récupération des outils métier réels
gmail_tools = composio_toolset.get_tools(apps=[App.GMAIL])
calendar_tools = composio_toolset.get_tools(apps=[App.GOOGLECALENDAR])
drive_tools = composio_toolset.get_tools(apps=[App.GOOGLEDRIVE])

# ==============================================================================
# 4. OUTILS MÉTIER SÉCURISÉS PAR CERBERE (Middleware transparent)
# ==============================================================================

@guard.guard_tool_call
def read_emails(query: str = "inbox", max_results: int = 10) -> Dict[str, Any]:
    """Lit les emails récents de la boîte Gmail."""
    try:
        response = composio_toolset.execute_action(
            action=Action.GMAIL_FETCH_EMAILS,
            params={"query": query, "max_results": max_results}
        )
        return {"status": "success", "emails": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Envoie un email via Gmail."""
    try:
        response = composio_toolset.execute_action(
            action=Action.GMAIL_SEND_EMAIL,
            params={"to": to, "subject": subject, "body": body}
        )
        return {"status": "sent", "message_id": response.get("id")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def check_calendar(date: str) -> Dict[str, Any]:
    """Vérifie les événements du calendrier pour une date donnée."""
    try:
        response = composio_toolset.execute_action(
            action=Action.GOOGLECALENDAR_GET_EVENTS,
            params={"date": date}
        )
        return {"status": "success", "events": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def create_calendar_event(title: str, date: str, time: str, duration: int = 60) -> Dict[str, Any]:
    """Crée un événement dans le calendrier."""
    try:
        response = composio_toolset.execute_action(
            action=Action.GOOGLECALENDAR_CREATE_EVENT,
            params={"title": title, "date": date, "time": time, "duration": duration}
        )
        return {"status": "created", "event_id": response.get("id")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def list_drive_files(query: str = "") -> Dict[str, Any]:
    """Liste les fichiers Google Drive."""
    try:
        response = composio_toolset.execute_action(
            action=Action.GOOGLEDRIVE_LIST_FILES,
            params={"query": query}
        )
        return {"status": "success", "files": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================================================================
# 5. SYSTEM PROMPT DE LUCE (Agent métier, pas agent de sécurité)
# ==============================================================================
LUCE_SYSTEM_PROMPT = """Tu es Luce, une assistante virtuelle intelligente et professionnelle 
spécialisée dans la gestion administrative pour les entreprises.

Tes responsabilités :
- Gérer les emails : lire, résumer, répondre, organiser
- Gérer le calendrier : vérifier les disponibilités, créer des rendez-vous
- Gérer les documents : lister, organiser les fichiers sur Google Drive
- Fournir des résumés et analyses pertinentes

Ton style :
- Professionnel, courtois, efficace
- Tu vas droit au but tout en restant agréable
- Tu poses des questions de clarification si nécessaire
- Tu proposes des solutions proactives

Outils disponibles :
- read_emails : Lire les emails (query, max_results)
- send_email : Envoyer un email (to, subject, body)
- check_calendar : Vérifier le calendrier (date)
- create_calendar_event : Créer un événement (title, date, time, duration)
- list_drive_files : Lister les fichiers Drive (query)

Important : Tu es une assistante métier, pas un outil de sécurité. 
Tu aides l'utilisateur à être productif dans son travail quotidien.
"""

# ==============================================================================
# 6. CERVEAU DE LUCE (Appel LLM avec gestion d'outils)
# ==============================================================================

@guard.guard_llm_call
def call_deepseek(messages: List[Dict[str, str]]) -> Any:
    """Appelle DeepSeek et retourne la réponse."""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.3,
        max_tokens=1000
    )
    return response

def luce_process_message(user_input: str, chat_history: List[Dict[str, str]]) -> tuple[str, str]:
    """
    Traite un message utilisateur et retourne (réponse, statut).
    Luce ne sait pas qu'elle est protégée par Cerbere.
    """
    # Construire le contexte
    messages = [{"role": "system", "content": LUCE_SYSTEM_PROMPT}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_input})
    
    try:
        # Appel LLM sécurisé par Cerbere (au niveau du prompt)
        response = call_deepseek(messages=messages)
        assistant_reply = response.choices[0].message.content
        
        # Détection basique d'intention d'outil (pour la démo)
        # Dans une vraie implémentation, on utiliserait le function calling d'OpenAI
        if "send_email" in user_input.lower() or "envoyer" in user_input.lower():
            # Simulation d'extraction de paramètres
            # En production, on parserait la réponse du LLM
            tool_result = send_email(
                to="recipient@example.com",  # À extraire dynamiquement
                subject="Message de Luce",
                body=assistant_reply
            )
            if tool_result["status"] == "sent":
                assistant_reply += "\n\n✅ Email envoyé avec succès."
            else:
                assistant_reply += f"\n\n❌ Erreur lors de l'envoi : {tool_result['message']}"
        
        elif "email" in user_input.lower() or "résumer" in user_input.lower():
            tool_result = read_emails(query="inbox", max_results=5)
            if tool_result["status"] == "success":
                assistant_reply += f"\n\n📧 J'ai trouvé {len(tool_result['emails'])} emails récents."
            else:
                assistant_reply += f"\n\n❌ Erreur lors de la lecture des emails : {tool_result['message']}"
        
        elif "calendrier" in user_input.lower() or "rendez-vous" in user_input.lower():
            tool_result = check_calendar(date="today")
            if tool_result["status"] == "success":
                assistant_reply += f"\n\n📅 J'ai vérifié votre calendrier."
            else:
                assistant_reply += f"\n\n❌ Erreur lors de la vérification : {tool_result['message']}"
        
        return assistant_reply, "ALLOWED"
    
    except SecurityException as e:
        # Cerbere a bloqué l'action (prompt injection, exfiltration, etc.)
        error_msg = str(e)
        return f"🛡️ Action bloquée par le système de sécurité : {error_msg}", "BLOCKED"
    
    except Exception as e:
        return f"❌ Erreur système : {str(e)}", "ERROR"
