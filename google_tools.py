from typing import Dict, Any

from googleapiclient.discovery import build

from google_auth import get_credentials


def get_gmail_service():

    credentials = get_credentials()

    if not credentials:
        return None

    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False
    )


def get_calendar_service():

    credentials = get_credentials()

    if not credentials:
        return None

    return build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False
    )


def get_drive_service():

    credentials = get_credentials()

    if not credentials:
        return None

    return build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False
    )


def read_emails(query="in:inbox", max_results=10):

    gmail = get_gmail_service()

    if not gmail:
        return {
            "status": "not_connected",
            "message": "Google n'est pas connecté."
        }

    try:

        result = gmail.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()

        messages = result.get("messages", [])

        emails = []

        for message in messages:

            data = gmail.users().messages().get(
                userId="me",
                id=message["id"],
                format="metadata",
                metadataHeaders=[
                    "From",
                    "To",
                    "Subject",
                    "Date"
                ]
            ).execute()

            headers = {
                header["name"].lower(): header["value"]
                for header in data
                .get("payload", {})
                .get("headers", [])
            }

            emails.append({
                "id": message["id"],
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", "")
            })

        return {
            "status": "success",
            "emails": emails
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


def read_email(message_id):

    gmail = get_gmail_service()

    if not gmail:
        return {
            "status": "not_connected"
        }

    try:

        message = gmail.users().messages().get(
            userId="me",
            id=message_id,
            format="full"
        ).execute()

        return {
            "status": "success",
            "message": message
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


def check_calendar():

    calendar = get_calendar_service()

    if not calendar:
        return {
            "status": "not_connected"
        }

    try:

        result = calendar.events().list(
            calendarId="primary",
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = []

        for event in result.get("items", []):

            events.append({
                "id": event.get("id"),
                "summary": event.get("summary", "Sans titre"),
                "start": event.get("start", {}),
                "end": event.get("end", {})
            })

        return {
            "status": "success",
            "events": events
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


def list_drive_files(query=""):

    drive = get_drive_service()

    if not drive:
        return {
            "status": "not_connected"
        }

    try:

        search_query = None

        if query:

            safe_query = query.replace("'", "\\'")

            search_query = (
                f"name contains '{safe_query}' "
                "and trashed = false"
            )

        result = drive.files().list(
            pageSize=20,
            q=search_query,
            fields="files(id,name,mimeType,modifiedTime)"
        ).execute()

        files = result.get("files", [])

        return {
            "status": "success",
            "files": files
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
