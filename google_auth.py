import os
import secrets
from urllib.parse import urljoin

from flask import session, redirect, request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:5000/auth/google/callback"
)

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",

    # Gmail
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",

    # Calendar
    "https://www.googleapis.com/auth/calendar.readonly",

    # Drive
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_client_config():
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [GOOGLE_REDIRECT_URI],
        }
    }


def create_google_flow():
    flow = Flow.from_client_config(
        get_client_config(),
        scopes=SCOPES
    )

    flow.redirect_uri = GOOGLE_REDIRECT_URI

    return flow


def start_google_auth():

    state = secrets.token_urlsafe(32)

    session["google_oauth_state"] = state

    flow = create_google_flow()

    authorization_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
        prompt="consent",
    )

    return authorization_url


def finish_google_auth():

    state = session.get("google_oauth_state")

    if not state:
        raise RuntimeError("OAuth state manquant.")

    flow = create_google_flow()

    flow.fetch_token(
        authorization_response=request.url
    )

    credentials = flow.credentials

    session["google_credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    session.pop("google_oauth_state", None)

    return credentials


def get_credentials():

    data = session.get("google_credentials")

    if not data:
        return None

    credentials = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(
            __import__("google.auth.transport.requests",
                       fromlist=["Request"]).Request()
        )

        session["google_credentials"]["token"] = credentials.token

    return credentials


def disconnect_google():

    session.pop("google_credentials", None)
    session.pop("google_oauth_state", None)
