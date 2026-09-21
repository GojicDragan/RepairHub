"""HTTP-Übersetzung; jede Identitätsaktion ruft einen injizierten Anwendungsfall auf."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_security import current_user
from flask_security.utils import get_message

from app.domains.users.check_reset_link.dto import Command as CheckReset
from app.domains.users.confirm_email.dto import Command as Confirm
from app.domains.users.login_user.dto import Command as Login
from app.domains.users.logout_user.dto import Command as Logout
from app.domains.users.register_user.dto import Command as Register
from app.domains.users.request_password_reset.dto import Command as RequestReset
from app.domains.users.resend_confirmation.dto import Command as Resend
from app.domains.users.reset_password.dto import Command as Reset


def create_user_blueprint(*, flows, forms):
    # Die Endpointnamen erhalten die Kompatibilität mit Mail-Links und Vorlagen
    # der Bibliothek. Die Routen gehören unserem eigenen Blueprint.
    blueprint = Blueprint("security", __name__)

    @blueprint.after_request
    def private_response(response):
        # Tokenpfade dürfen weder aus dem Browsercache wiedererscheinen noch
        # beim Navigieren als Referer an andere Ziele weitergegeben werden.
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def execute(name, command, form=None):
        result = flows[name].execute(command)
        if result.code in {"conflict", "unavailable"}:
            abort(409 if result.code == "conflict" else 503)
        if form is not None:
            for field, messages in result.errors:
                if field and field in form:
                    form[field].errors = list(messages)
                else:
                    form.form_errors.extend(messages)
        return result

    def message(code, **values):
        text, category = get_message(code, **values)
        flash(text, category)

    @blueprint.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("web.index"))
        form = forms["register_form"]()
        if request.method == "POST":
            result = execute(
                "register",
                Register(
                    request.form.get("username", ""),
                    request.form.get("email", ""),
                    request.form.get("password", ""),
                    request.form.get("password_confirm", ""),
                ),
                form,
            )
            if result.code == "ok":
                return redirect(url_for("web.index"))
        return render_template("security/register_user.html", register_user_form=form)

    @blueprint.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("web.index"))
        form = forms["login_form"]()
        if request.method == "POST":
            result = execute(
                "login",
                Login(
                    request.form.get("identity", ""),
                    request.form.get("password", ""),
                    request.form.get("remember", "") in {"y", "true", "on", "1"},
                ),
                form,
            )
            if result.code == "ok":
                # Ein festes Ziel verhindert Weiterleitungen an vom Client vorgegebene URLs.
                return redirect(url_for("web.index"))
        return render_template("security/login_user.html", login_user_form=form)

    @blueprint.post("/logout")
    def logout():
        execute("logout", Logout())
        return redirect(url_for("web.index"))

    @blueprint.route("/confirm", methods=["GET", "POST"])
    def send_confirmation():
        form = forms["send_confirmation_form"]()
        if request.method == "POST":
            email = request.form.get("email", "")
            execute("resend", Resend(email), form)
            message("CONFIRMATION_REQUEST", email=email)
        return render_template("security/send_confirmation.html", send_confirmation_form=form)

    @blueprint.get("/confirm/<token>")
    def confirm_email(token):
        result = execute("confirm", Confirm(token))
        if result.code != "ok":
            message(
                "ALREADY_CONFIRMED"
                if result.code == "already_confirmed"
                else "INVALID_CONFIRMATION_TOKEN"
            )
            return redirect(url_for("security.send_confirmation"))
        message("EMAIL_CONFIRMED")
        return redirect(url_for("security.login"))

    @blueprint.route("/reset", methods=["GET", "POST"])
    def forgot_password():
        form = forms["forgot_password_form"]()
        if request.method == "POST":
            email = request.form.get("email", "")
            execute("request_reset", RequestReset(email), form)
            message("PASSWORD_RESET_REQUEST", email=email)
        return render_template("security/forgot_password.html", forgot_password_form=form)

    @blueprint.route("/reset/<token>", methods=["GET", "POST"])
    def reset_password(token):
        form = forms["reset_password_form"]()
        if request.method == "POST":
            result = execute(
                "reset",
                Reset(
                    token,
                    request.form.get("password", ""),
                    request.form.get("password_confirm", ""),
                ),
                form,
            )
            if result.code == "ok":
                message("PASSWORD_RESET_NO_LOGIN")
                return redirect(url_for("security.login"))
        else:
            result = execute("check_reset", CheckReset(token))
        if result.code == "invalid_token":
            message("INVALID_RESET_PASSWORD_TOKEN")
            return redirect(url_for("security.forgot_password"))
        return render_template(
            "security/reset_password.html", reset_password_form=form, reset_password_token=token
        )

    return blueprint
