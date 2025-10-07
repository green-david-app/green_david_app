
import os, traceback
from flask import Flask, session, redirect, request, Response, render_template_string

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

BASE = """
<!doctype html>
<html lang="cs">
  <head><meta charset="utf-8"><title>{{ title }}</title></head>
  <body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial">
    <h1>{{ title }}</h1>
    <div>{% block content %}{% endblock %}</div>
    <hr><small>green david app — DEBUG TEMP</small>
  </body>
</html>
"""

@app.errorhandler(Exception)
def handle_ex(e):
    tb = traceback.format_exc()
    print(tb, flush=True)  # log to stdout for Render logs
    body = f"<h2>500 Internal Server Error (DEBUG TEMP)</h2><pre>{tb}</pre>"
    return Response(body, status=500, content_type="text/html; charset=utf-8")

@app.route("/", endpoint="root")
def root():
    if not session.get("uid"):
        return redirect("/login")
    return render_template_string(BASE + "{% block content %}<p>Dashboard OK (uživatel {{session['uid']}})</p>{% endblock %}", title="Dashboard")

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        return render_template_string(BASE + """
        {% block content %}
        <form method="post">
          <label>Email <input name="email" type="email" required></label><br>
          <label>Heslo <input name="password" type="password" required></label><br>
          <button type="submit">Přihlásit</button>
        </form>
        {% endblock %}""", title="Přihlášení")
    session["uid"] = request.form.get("email") or "user"
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/healthz")
def healthz():
    return {"ok": True}
