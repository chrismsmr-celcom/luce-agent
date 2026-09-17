import os
import json
import base64
from typing import List, Dict, Any
from email.mime.text import MIMEText
from openai import OpenAI
from dotenv import load_dotenv
from agentguard import AgentGuard, SecurityException

# Imports Google API
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
# 3. INITIALISATION DIRECTE DES GOOGLE APIS
# ==============================================================================
google_error = None
gmail_service = None
calendar_service = None
drive_service = None

try:
    # On récupère le JSON du compte de service depuis les variables d'environnement Render
    service_account_info_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    service_account_info = json.loads(service_account_info_str)
    
    if "client_email" in service_account_info:
        SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        
        creds = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )
        
        # Construction des clients API
        gmail_service = build('gmail', 'v1', credentials=creds)
        calendar_service = build('calendar', 'v3', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        print("✅ Google API Services initialisés avec succès.")
    else:
        google_error = "GOOGLE_SERVICE_ACCOUNT_JSON manquante ou invalide dans les variables d'environnement."
        print(f"⚠️ GOOGLE WARNING: {google_error}")
        
except Exception as e:
    google_error = f"Erreur d'initialisation Google API : {str(e)}"
    print(f"⚠️ GOOGLE WARNING: {google_error}")

# ==============================================================================
# 4. OUTILS MÉTIER (Protégés par Cerbere)
# ==============================================================================

@guard.guard_tool_call
def read_emails(query: str = "inbox", max_results: int = 5) -> Dict[str, Any]:
    """Lit les emails récents via l'API Gmail."""
    if gmail_service is None:
        return {"status": "error", "message": f"Google API indisponible : {google_error}"}
    try:
        results = gmail_service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        emails = []
        for msg in messages:
            # On récupère juste les métadonnées pour être rapide et léger
            msg_data = gmail_service.users().messages().get(
                userId='me', id=msg['id'], format='metadata', 
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sans objet')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Inconnu')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Inconnue')
            emails.append({"id": msg['id'], "from": sender, "subject": subject, "date": date})
        return {"status": "success", "emails": emails}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Envoie un email via l'API Gmail."""
    if gmail_service is None:
        return {"status": "error", "message": f"Google API indisponible : {google_error}"}
    try:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent_message = gmail_service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        return {"status": "sent", "message_id": sent_message.get('id')}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def check_calendar(date: str = "today") -> Dict[str, Any]:
    """Vérifie les événements du calendrier."""
    if calendar_service is None:
        return {"status": "error", "message": f"Google API indisponible : {google_error}"}
    try:
        events_result = calendar_service.events().list(
            calendarId='primary', maxResults=5, singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        calendar_events = [
            {"summary": event.get('summary', 'Sans titre'), 
             "start": event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))} 
            for event in events
        ]
        return {"status": "success", "events": calendar_events}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@guard.guard_tool_call
def list_drive_files(query: str = "") -> Dict[str, Any]:
    """Liste les fichiers Google Drive."""
    if drive_service is None:
        return {"status": "error", "message": f"Google API indisponible : {google_error}"}
    try:
        search_query = f"name contains '{query}'" if query else ""
        results = drive_service.files().list(pageSize=5, q=search_query, spaces='drive').execute()
        files = results.get('files', [])
        drive_files = [{"name": f.get('name'), "mimeType": f.get('mimeType')} for f in files]
        return {"status": "success", "files": drive_files}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==============================================================================
# 5. SYSTEM PROMPT DE LUCE
# ==============================================================================
LUCE_SYSTEM_PROMPT = """Tu es Luce, une assistante virtuelle professionnelle spécialisée dans la gestion administrative.
Tu gères les emails, le calendrier et les documents Drive. 
Style : Professionnel, efficace, proactif. Tu vas droit au but.
"""

# ==============================================================================
# 6. CERVEAU DE LUCE
# ==============================================================================

@guard.guard_llm_call
def call_deepseek(messages: List[Dict[str, str]]) -> Any:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.3,
        max_tokens=1000
    )
    return response

def luce_process_message(user_input: str, chat_history: List[Dict[str, str]]) -> tuple[str, str]:
    messages = [{"role": "system", "content": LUCE_SYSTEM_PROMPT}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_input})
    
    try:
        response = call_deepseek(messages=messages)
        assistant_reply = response.choices[0].message.content
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ["envoyer", "envoie", "send", "transférer"]):
            tool_result = send_email(to="recipient@example.com", subject="Message de Luce", body=assistant_reply[:500])
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
