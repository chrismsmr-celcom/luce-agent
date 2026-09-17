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
    raise RuntimeError(
        "COMPOSIO_API_KEY is missing"
    )


composio = Composio(
    api_key=COMPOSIO_API_KEY
)


# ---------------------------------------------------------
# SESSION
# ---------------------------------------------------------

def get_or_create_session(user_id: str):
    """
    Return the persistent Composio session for a Luce user.

    The session ID is stored in our database.

    If the user already has a session:
        composio.use(session_id)

    Otherwise:
        composio.sessions.create(...)
    """

    if not user_id:
        raise ValueError(
            "user_id is required"
        )

    # -----------------------------------------------------
    # Try to restore an existing session
    # -----------------------------------------------------

    session_id = get_composio_session_id(
        user_id
    )

    if session_id:

        try:

            session = composio.use(
                session_id
            )

            return session

        except Exception as exc:

            print(
                "Could not restore Composio session:",
                exc,
            )

    # -----------------------------------------------------
    # Create a new persistent session
    # -----------------------------------------------------

    session = composio.sessions.create(
        user_id=user_id,

        toolkits=[
            "gmail",
            "googlecalendar",
            "googledrive",
        ],

        sandbox={
            "enable": False
        },
    )

    # -----------------------------------------------------
    # Persist session ID
    # -----------------------------------------------------

    save_composio_session_id(
        user_id=user_id,
        session_id=session.session_id,
    )

    return session


# ---------------------------------------------------------
# TOOLS
# ---------------------------------------------------------

def get_tools(user_id: str):
    """
    Return tools available to this user's session.
    """

    session = get_or_create_session(
        user_id
    )

    return session.tools()


# ---------------------------------------------------------
# AUTHORIZATION
# ---------------------------------------------------------

def authorize_toolkit(
    user_id: str,
    toolkit: str,
    callback_url: str | None = None,
):
    """
    Start Composio OAuth authorization.

    The user is redirected to the Composio Connect Link.
    """

    session = get_or_create_session(
        user_id
    )

    connection_request = session.authorize(
        toolkit=toolkit,
        callback_url=callback_url,
    )

    return {
        "id": getattr(
            connection_request,
            "id",
            None,
        ),

        "redirect_url": (
            connection_request.redirect_url
        ),
    }


# ---------------------------------------------------------
# EXECUTE TOOL
# ---------------------------------------------------------

def execute_tool(
    user_id: str,
    tool_slug: str,
    arguments: dict[str, Any],
):
    """
    Execute a Composio tool inside the user's
    persistent session.
    """

    session = get_or_create_session(
        user_id
    )

    return session.execute(
        tool_slug,
        arguments=arguments,
    )


# ---------------------------------------------------------
# CONNECTED ACCOUNTS
# ---------------------------------------------------------

def list_connected_accounts(
    user_id: str,
):
    """
    Return all connected accounts for a user.
    """

    response = composio.connected_accounts.list(
        user_ids=[user_id],
        statuses=["ACTIVE"],
    )

    # Current Composio SDK returns a response
    # containing .items.
    return getattr(
        response,
        "items",
        [],
    )
