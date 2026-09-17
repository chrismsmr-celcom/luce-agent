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


def get_or_create_session(user_id: str):
    """
    Get the existing Composio session for the user.
    Create one if it does not exist.
    """

    if not user_id:
        raise ValueError("user_id is required")

    # ---------------------------------------------------------
    # 1. Try to restore an existing session
    # ---------------------------------------------------------

    session_id = get_composio_session_id(user_id)

    if session_id:
        try:
            session = composio.use(session_id)

            print(
                f"[Composio] Restored session "
                f"{session_id} for user {user_id}"
            )

            return session

        except Exception as exc:
            print(
                f"[Composio] Could not restore session "
                f"{session_id}: {exc}"
            )

    # ---------------------------------------------------------
    # 2. Create a new session
    # ---------------------------------------------------------

    session = composio.create(
        user_id=user_id,
        toolkits=[
            "gmail",
            "googlecalendar",
            "googledrive",
        ],
        sandbox={
            "enable": False,
        },
    )

    # ---------------------------------------------------------
    # 3. Persist the session ID
    # ---------------------------------------------------------

    save_composio_session_id(
        user_id=user_id,
        session_id=session.session_id,
    )

    print(
        f"[Composio] Created session "
        f"{session.session_id} for user {user_id}"
    )

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
        "id": getattr(
            connection_request,
            "id",
            None,
        ),
        "redirect_url": connection_request.redirect_url,
    }


def execute_tool(
    user_id: str,
    tool_slug: str,
    arguments: dict[str, Any],
):
    """
    Execute a Composio tool inside the user's session.
    """

    session = get_or_create_session(user_id)

    return session.execute(
        tool_slug,
        arguments=arguments,
    )


def list_connected_accounts(user_id: str):
    """
    Return active Composio connected accounts
    for this user.
    """

    response = composio.connected_accounts.list(
        user_ids=[user_id],
        statuses=["ACTIVE"],
    )

    return getattr(
        response,
        "items",
        [],
    )
