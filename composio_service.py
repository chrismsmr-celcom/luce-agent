import os
from functools import lru_cache

from composio import Composio


COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")

if not COMPOSIO_API_KEY:
    raise RuntimeError("COMPOSIO_API_KEY is missing")


composio = Composio(api_key=COMPOSIO_API_KEY)


@lru_cache(maxsize=1000)
def get_session(user_id: str):
    """
    Returns a Composio session scoped to one Luce user.

    IMPORTANT:
    Never use one global user_id for every customer.
    """

    return composio.create(user_id=user_id)


def get_tools(user_id: str):
    """
    Get tools available to this user's Composio session.
    """

    session = get_session(user_id)

    return session.tools()


def authorize_toolkit(
    user_id: str,
    toolkit: str,
    callback_url: str | None = None,
):
    """
    Starts OAuth authorization for a toolkit.

    Example:
        authorize_toolkit("user_123", "gmail", callback_url)
    """

    session = get_session(user_id)

    connection = session.authorize(
        toolkit=toolkit,
        callback_url=callback_url,
    )

    return {
        "id": getattr(connection, "id", None),
        "redirect_url": connection.redirect_url,
    }


def execute_tool(
    user_id: str,
    tool_slug: str,
    arguments: dict,
):
    """
    Execute a Composio tool inside the user's session.
    """

    session = get_session(user_id)

    result = session.execute(
        tool_slug,
        arguments=arguments,
    )

    return result


def list_connected_accounts(user_id: str):
    """
    Return the user's Composio connections.
    """

    accounts = composio.connected_accounts.list(
        user_ids=[user_id],
    )

    return accounts
