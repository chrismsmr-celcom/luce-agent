import os
import uuid

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
)

from agent import process_message
from composio_service import (
    authorize_toolkit,
    list_connected_accounts,
)


load_dotenv()


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is missing")


# ---------------------------------------------------------
# DEMO USER
# ---------------------------------------------------------
#
# IMPORTANT:
# For production, replace this with the authenticated
# user's real database ID.
#
DEMO_USER_ID = "luce_demo_user"


# ---------------------------------------------------------
# FRONTEND
# ---------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "luce",
    })


# ---------------------------------------------------------
# COMPOSIO CONNECTION
# ---------------------------------------------------------

@app.post("/api/connect/<toolkit>")
def connect_toolkit(toolkit):

    allowed = {
        "gmail",
        "googlecalendar",
        "googledrive",
    }

    if toolkit not in allowed:
        return jsonify({
            "error": "Unsupported toolkit"
        }), 400

    try:

        callback_url = (
            request.host_url.rstrip("/")
            + "/api/composio/callback"
        )

        connection = authorize_toolkit(
            user_id=DEMO_USER_ID,
            toolkit=toolkit,
            callback_url=callback_url,
        )

        return jsonify(connection)

    except Exception as exc:

        app.logger.exception(
            "Composio authorization failed"
        )

        return jsonify({
            "error": str(exc)
        }), 500


# ---------------------------------------------------------
# COMPOSIO CALLBACK
# ---------------------------------------------------------

@app.get("/api/composio/callback")
def composio_callback():

    # Composio handles the actual connection.
    #
    # The callback is mainly used to return the user
    # to Luce after authentication.

    return redirect("/")


# ---------------------------------------------------------
# CONNECTION STATUS
# ---------------------------------------------------------

@app.get("/api/connections")
def connections():

    try:

        accounts = list_connected_accounts(
            DEMO_USER_ID
        )

        result = {
            "gmail": False,
            "googlecalendar": False,
            "googledrive": False,
        }

        for account in accounts:

            status = str(
                getattr(account, "status", "")
            ).upper()

            if status != "ACTIVE":
                continue

            toolkit = getattr(
                getattr(account, "toolkit", None),
                "slug",
                "",
            )

            toolkit = str(toolkit).lower()

            if toolkit in result:
                result[toolkit] = True

        return jsonify(result)

    except Exception as exc:

        app.logger.exception(
            "Could not retrieve connections"
        )

        return jsonify({
            "error": str(exc)
        }), 500


# ---------------------------------------------------------
# CHAT
# ---------------------------------------------------------

@app.post("/api/chat")
def chat():

    data = request.get_json(silent=True) or {}

    message = str(
        data.get("message", "")
    ).strip()

    if not message:
        return jsonify({
            "error": "Message is required"
        }), 400

    try:

        result = process_message(
            user_id=DEMO_USER_ID,
            message=message,
        )

        return jsonify(result)

    except Exception as exc:

        app.logger.exception(
            "Luce processing failed"
        )

        return jsonify({
            "error": str(exc)
        }), 500


# ---------------------------------------------------------
# START
# ---------------------------------------------------------

if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "10000")
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
