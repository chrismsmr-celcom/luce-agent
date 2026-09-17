import os

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    session
)

from google_auth import (
    start_google_auth,
    finish_google_auth,
    get_credentials,
    disconnect_google
)

from google_tools import (
    read_emails,
    check_calendar,
    list_drive_files
)


app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "CHANGE_THIS_SECRET_IN_PRODUCTION"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ============================================================
# FRONTEND
# ============================================================

@app.route("/")
def index():

    return render_template("index.html")


# ============================================================
# GOOGLE OAUTH
# ============================================================

@app.route("/auth/google")
def google_login():

    authorization_url = start_google_auth()

    return redirect(authorization_url)


@app.route("/auth/google/callback")
def google_callback():

    try:

        finish_google_auth()

        return redirect("/?google=connected")

    except Exception as e:

        return redirect(
            "/?google=error"
        )


@app.route("/auth/google/disconnect")
def google_disconnect():

    disconnect_google()

    return redirect("/?google=disconnected")


@app.route("/api/connections")
def connections():

    connected = bool(get_credentials())

    return jsonify({
        "google": connected,
        "gmail": connected,
        "calendar": connected,
        "drive": connected
    })


# ============================================================
# GMAIL
# ============================================================

@app.route("/api/gmail/emails")
def gmail_emails():

    result = read_emails(
        query="in:inbox",
        max_results=10
    )

    return jsonify(result)


# ============================================================
# CALENDAR
# ============================================================

@app.route("/api/calendar/events")
def calendar_events():

    result = check_calendar()

    return jsonify(result)


# ============================================================
# DRIVE
# ============================================================

@app.route("/api/drive/files")
def drive_files():

    result = list_drive_files()

    return jsonify(result)


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok"
    })


if __name__ == "__main__":

    port = int(os.getenv("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
