import os
from typing import Any

from dotenv import load_dotenv
from composio import Composio

from database import (
    get_composio_session_id,
    save_composio_session_id,
)

load_dotenv()


COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")

if not COMPOSIO_API_KEY:
    raise RuntimeError("COMPOSIO_API_KEY is missing")


composio = Composio(
    api_key=COMPOSIO_API_KEY
)

# GitHub est maintenant inclus dans les toolkits
TOOLKITS = [
    "gmail",
    "googlecalendar",
    "googledrive",
    "github",
]

# Bump this number whenever TOOLKITS changes.
# Sessions saved with an older version are NOT restored:
# a new session (with the new toolkits) is created instead.
# This fixes: "Toolkit 'github' is not allowed for this session"
SESSION_VERSION = 2


def _toolkit_not_allowed(exc: Exception) -> bool:
    """Detect Composio's session-restriction error (code 4324)."""
    text = str(exc)
    return (
        "ToolkitNotAllowed" in text
        or "is not allowed for this session" in text
    )


def get_or_create_session(user_id: str):
    """
    Get the existing Composio session for the user.
    Create one if it does not exist.

    The session ID is stored with a version prefix.
    If SESSION_VERSION changed (toolkits added/removed),
    the old session is discarded and a new one is created
    with the updated toolkit list.
    """

    if not user_id:
        raise ValueError("user_id is required")

    version_prefix = f"v{SESSION_VERSION}:"

    # 1. Try to restore an existing session (only if same version)

    stored = get_composio_session_id(user_id)

    if stored and stored.startswith(version_prefix):

        session_id = stored[len(version_prefix):]

        try:
            session = composio.use(session_id)
            print(f"[Composio] Restored session {session_id} for user {user_id}")
            return session
        except Exception as exc:
            print(f"[Composio] Could not restore session {session_id}: {exc}")

    elif stored:
        print(
            f"[Composio] Session version mismatch (stored: {stored.split(':')[0]}, "
            f"current: v{SESSION_VERSION}). Creating a new session."
        )

    # 2. Create a new session

    session = composio.create(
        user_id=user_id,
        toolkits=TOOLKITS,
        sandbox={"enable": False},
    )

    # 3. Persist the session ID (versioned)

    save_composio_session_id(
        user_id=user_id,
        session_id=version_prefix + session.session_id,
    )

    print(f"[Composio] Created session {session.session_id} for user {user_id}")

    return session


def get_tools(user_id: str):
    """
    Return tools exposed by the user's Composio session.
    """
    session = get_or_create_session(user_id)
    return session.tools()


def authorize_toolkit(
    user_id: str,
    toolkit: str,
    callback_url: str | None = None,
):
    """
    Start OAuth authorization for a toolkit.
    """
    session = get_or_create_session(user_id)

    connection_request = session.authorize(
        toolkit,
        callback_url=callback_url,
    )

    return {
        "id": getattr(connection_request, "id", None),
        "redirect_url": connection_request.redirect_url,
    }


def execute_tool(
    user_id: str,
    tool_slug: str,
    arguments: dict[str, Any],
):
    """
    Execute a Composio tool inside the user's session.

    If Composio rejects the tool because the session was
    created with an older toolkit list, recreate the session
    and retry once.
    """
    session = get_or_create_session(user_id)

    try:
        return session.execute(tool_slug, arguments=arguments)
    except Exception as exc:

        if not _toolkit_not_allowed(exc):
            raise

        print(
            f"[Composio] Toolkit not allowed on current session "
            f"({tool_slug}). Recreating session and retrying..."
        )

        # Force a fresh session (bypasses the versioned restore)
        save_composio_session_id(user_id=user_id, session_id="")
        session = get_or_create_session(user_id)

        return session.execute(tool_slug, arguments=arguments)


def list_connected_accounts(user_id: str):
    """
    Return active Composio connected accounts for this user.
    """
    response = composio.connected_accounts.list(
        user_ids=[user_id],
        statuses=["ACTIVE"],
    )
    return getattr(response, "items", [])
