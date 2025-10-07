
import os
from flask import Flask, session, redirect, request, render_template_string, Response

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

BASE = """
<!doctype html>
<html lang="cs">
  <head><meta charset="utf-8"><title>{{ title }}</title></head>
  <body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial">
    <h1>{{ title }}</h1>
    <div>{{ body|safe }}</div>
    <hr><small>green david app — DEBUG TEMP</small>
  </body>
</html>
"""

@app.errorhandler(Exception)
def handle_ex(e):
    import traceback
    tb = traceback.format_exc()
    print(tb, flush=True)
    return Response(f"<h2>500 Internal Server Error (DEBUG TEMP)</h2><pre>{tb}</pre>", status=500, content_type="text/html; charset=utf-8")

@app.route("/", endpoint="root")
def root():
    if not session.get("uid"):
        return redirect("/login")
    body = "<p>Dashboard OK (uživatel {})</p>".format(session['uid'])
    return render_template_string(BASE, title="Dashboard", body=body)

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        form = """
        <form method="post">
          <label>Email <input name="email" type="email" required></label><br>
          <label>Heslo <input name="password" type="password" required></label><br>
          <button type="submit">Přihlásit</button>
        </form>
        """
        return render_template_string(BASE, title="Přihlášení", body=form)
    session["uid"] = request.form.get("email") or "user"
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/healthz")
def healthz():
    return {"ok": True}
