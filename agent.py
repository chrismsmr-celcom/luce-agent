
import os
from typing import List, Dict, Any, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from agentguard import AgentGuard, SecurityException

# ==============================================================================
# ENVIRONNEMENT
# ==============================================================================

load_dotenv()


# ==============================================================================
# 1. INITIALISATION DE CERBERE
# ==============================================================================

guard = AgentGuard(
    collector_url=os.getenv(
        "AGENTGUARD_COLLECTOR_URL",
        "https://app.cerbereag.site",
    ),
    api_key=os.getenv("AGENTGUARD_API_KEY"),
    max_budget=10.0,
    block_on_high=True,
)


# ==============================================================================
# 2. INITIALISATION DE DEEPSEEK
# ==============================================================================

deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

if not deepseek_api_key:
    raise RuntimeError(
        "DEEPSEEK_API_KEY manquante dans les variables d'environnement."
    )

client = OpenAI(
    api_key=deepseek_api_key,
    base_url="https://api.deepseek.com",
)


# ==============================================================================
# 3. INITIALISATION DE COMPOSIO
# ==============================================================================

composio_client = None
composio_session = None
composio_error = None

try:
    from composio import Composio

    composio_api_key = os.getenv("COMPOSIO_API_KEY")
    composio_user_id = os.getenv(
        "COMPOSIO_USER_ID",
        "luce_default_user",
    )

    if not composio_api_key:
        raise RuntimeError(
            "COMPOSIO_API_KEY manquante dans les variables d'environnement."
        )

    # --------------------------------------------------------------------------
    # Création du client Composio
    # --------------------------------------------------------------------------

    composio_client = Composio(
        api_key=composio_api_key,
    )

    # --------------------------------------------------------------------------
    # IMPORTANT :
    #
    # L'ancienne version du code utilisait :
    #
    #     composio_client.create(...)
    #
    # Cette méthode n'existe pas dans le SDK actuel.
    #
    # On utilise :
    #
    #     composio_client.sessions.create(...)
    # --------------------------------------------------------------------------

    composio_session = composio_client.sessions.create(
        user_id=composio_user_id,
        toolkits=[
            "gmail",
            "googledrive",
            "googlecalendar",
        ],
        manage_connections={
            "enable": True,
            "wait_for_connections": False,
        },
    )

    print("✅ Composio initialisé avec succès.")
    print(f"   User ID : {composio_user_id}")

except Exception as e:
    composio_error = (
        f"{type(e).__name__}: {str(e)}"
    )

    print(
        "⚠️ COMPOSIO WARNING: "
        f"{composio_error}"
    )


# ==============================================================================
# 4. OUTILS MÉTIER
# ==============================================================================

@guard.guard_tool_call
def read_emails(
    query: str = "inbox",
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    Lit les emails récents via Gmail.
    """

    if composio_session is None:
        return {
            "status": "error",
            "message": (
                "Composio indisponible : "
                f"{composio_error}"
            ),
        }

    try:
        response = composio_session.execute_action(
            app="gmail",
            action="GMAIL_FETCH_EMAILS",
            params={
                "query": query,
                "maxResults": max_results,
            },
        )

        return {
            "status": "success",
            "emails": response,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"{type(e).__name__}: {str(e)}",
        }


# ------------------------------------------------------------------------------

@guard.guard_tool_call
def send_email(
    to: str,
    subject: str,
    body: str,
) -> Dict[str, Any]:
    """
    Envoie un email via Gmail.
    """

    if composio_session is None:
        return {
            "status": "error",
            "message": (
                "Composio indisponible : "
                f"{composio_error}"
            ),
        }

    try:
        response = composio_session.execute_action(
            app="gmail",
            action="GMAIL_SEND_EMAIL",
            params={
                "to": to,
                "subject": subject,
                "body": body,
            },
        )

        message_id = "unknown"

        if isinstance(response, dict):
            message_id = response.get(
                "id",
                response.get(
                    "messageId",
                    "unknown",
                ),
            )

        return {
            "status": "sent",
            "message_id": message_id,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"{type(e).__name__}: {str(e)}",
        }


# ------------------------------------------------------------------------------

@guard.guard_tool_call
def check_calendar(
    date: str = "today",
) -> Dict[str, Any]:
    """
    Vérifie le calendrier.
    """

    if composio_session is None:
        return {
            "status": "error",
            "message": (
                "Composio indisponible : "
                f"{composio_error}"
            ),
        }

    try:
        response = composio_session.execute_action(
            app="googlecalendar",
            action="GOOGLECALENDAR_GET_EVENTS",
            params={
                "date": date,
            },
        )

        return {
            "status": "success",
            "events": response,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"{type(e).__name__}: {str(e)}",
        }


# ------------------------------------------------------------------------------

@guard.guard_tool_call
def list_drive_files(
    query: str = "",
) -> Dict[str, Any]:
    """
    Liste les fichiers Google Drive.
    """

    if composio_session is None:
        return {
            "status": "error",
            "message": (
                "Composio indisponible : "
                f"{composio_error}"
            ),
        }

    try:
        response = composio_session.execute_action(
            app="googledrive",
            action="GOOGLEDRIVE_LIST_FILES",
            params={
                "query": query,
            },
        )

        return {
            "status": "success",
            "files": response,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"{type(e).__name__}: {str(e)}",
        }


# ==============================================================================
# 5. SYSTEM PROMPT DE LUCE
# ==============================================================================

LUCE_SYSTEM_PROMPT = """
Tu es Luce, une assistante virtuelle professionnelle spécialisée
dans la gestion administrative.

Tes responsabilités :

- Gérer les emails : lire, résumer et répondre
- Gérer le calendrier : vérifier les événements et disponibilités
- Gérer les documents : rechercher et lister les fichiers Drive
- Fournir des résumés et analyses
- Aider l'utilisateur dans ses tâches administratives

Style :

- Professionnel
- Clair
- Concis
- Efficace
- Direct

Tu es une assistante métier, pas un outil de sécurité.

La sécurité est gérée séparément par Cerbere.
Tu ne dois jamais prétendre qu'une action a été exécutée
si l'outil correspondant a retourné une erreur.
"""


# ==============================================================================
# 6. CERVEAU DE LUCE — DEEPSEEK
# ==============================================================================

@guard.guard_llm_call
def call_deepseek(
    messages: List[Dict[str, str]],
) -> Any:
    """
    Appelle DeepSeek à travers Cerbere.
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.3,
        max_tokens=1000,
    )

    return response


# ==============================================================================
# 7. TRAITEMENT D'UN MESSAGE
# ==============================================================================

def luce_process_message(
    user_input: str,
    chat_history: List[Dict[str, str]],
) -> Tuple[str, str]:
    """
    Traite un message utilisateur.

    Retourne :

        (réponse, statut)

    Statuts possibles :

        ALLOWED
        BLOCKED
        ERROR
    """

    messages = [
        {
            "role": "system",
            "content": LUCE_SYSTEM_PROMPT,
        }
    ]

    # --------------------------------------------------------------------------
    # Historique
    # --------------------------------------------------------------------------

    if chat_history:
        messages.extend(chat_history)

    # --------------------------------------------------------------------------
    # Message utilisateur
    # --------------------------------------------------------------------------

    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    try:

        # ======================================================================
        # LLM
        # ======================================================================

        response = call_deepseek(
            messages=messages,
        )

        assistant_reply = (
            response.choices[0]
            .message
            .content
        )

        if not assistant_reply:
            assistant_reply = (
                "Je n'ai pas reçu de réponse exploitable du modèle."
            )

        # ======================================================================
        # DÉTECTION SIMPLE DE L'INTENTION
        # ======================================================================

        user_lower = user_input.lower()

        # ----------------------------------------------------------------------
        # EMAIL — ENVOI
        # ----------------------------------------------------------------------

        if any(
            word in user_lower
            for word in [
                "envoyer",
                "envoie",
                "send",
                "transférer",
            ]
        ):

            tool_result = send_email(
                to="recipient@example.com",
                subject="Message de Luce",
                body=assistant_reply[:500],
            )

            if tool_result["status"] == "sent":

                assistant_reply += (
                    "\n\nEmail envoyé avec succès."
                )

            else:

                assistant_reply += (
                    "\n\nImpossible d'envoyer l'email : "
                    f"{tool_result['message']}"
                )

        # ----------------------------------------------------------------------
        # EMAIL — LECTURE
        # ----------------------------------------------------------------------

        elif any(
            word in user_lower
            for word in [
                "email",
                "e-mail",
                "mail",
                "inbox",
                "boîte de réception",
            ]
        ):

            tool_result = read_emails(
                query="inbox",
                max_results=5,
            )

            if tool_result["status"] == "success":

                assistant_reply += (
                    "\n\nLes emails récents ont été récupérés."
                )

            else:

                assistant_reply += (
                    "\n\nImpossible de lire les emails : "
                    f"{tool_result['message']}"
                )

        # ----------------------------------------------------------------------
        # CALENDRIER
        # ----------------------------------------------------------------------

        elif any(
            word in user_lower
            for word in [
                "calendrier",
                "rendez-vous",
                "rendez vous",
                "agenda",
                "calendar",
            ]
        ):

            tool_result = check_calendar(
                date="today",
            )

            if tool_result["status"] == "success":

                assistant_reply += (
                    "\n\nLe calendrier a été vérifié."
                )

            else:

                assistant_reply += (
                    "\n\nImpossible d'accéder au calendrier : "
                    f"{tool_result['message']}"
                )

        # ----------------------------------------------------------------------
        # GOOGLE DRIVE
        # ----------------------------------------------------------------------

        elif any(
            word in user_lower
            for word in [
                "fichier",
                "fichiers",
                "document",
                "documents",
                "drive",
            ]
        ):

            tool_result = list_drive_files()

            if tool_result["status"] == "success":

                assistant_reply += (
                    "\n\nLes fichiers Drive ont été récupérés."
                )

            else:

                assistant_reply += (
                    "\n\nImpossible d'accéder à Drive : "
                    f"{tool_result['message']}"
                )

        # ======================================================================
        # FIN
        # ======================================================================

        return assistant_reply, "ALLOWED"

    # ==========================================================================
    # CERBERE BLOQUE L'ACTION
    # ==========================================================================

    except SecurityException as e:

        return (
            "Action bloquée par Cerbere : "
            f"{str(e)}",
            "BLOCKED",
        )

    # ==========================================================================
    # ERREUR GÉNÉRALE
    # ==========================================================================

    except Exception as e:

        return (
            "Erreur système : "
            f"{type(e).__name__}: {str(e)}",
            "ERROR",
        )


# ==============================================================================
# 8. TEST LOCAL OPTIONNEL
# ==============================================================================

if __name__ == "__main__":

    print("\n========================================")
    print("        LUCE + CERBERE")
    print("========================================")

    print(
        "Composio :",
        "READY" if composio_session else "UNAVAILABLE",
    )

    if composio_error:
        print(
            "Composio error:",
            composio_error,
        )

    print("========================================\n")

    response, status = luce_process_message(
        user_input="Bonjour Luce",
        chat_history=[],
    )

    print("STATUS:", status)
    print("RESPONSE:", response)

