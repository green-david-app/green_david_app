Deploy notes (Render.com)

1) In Settings -> Start Command set:
   gunicorn main:app

2) In Environment, ensure SECRET_KEY is set (any random string).
   Optional: ADMIN_EMAIL, ADMIN_NAME, ADMIN_PASSWORD to seed the first admin.

3) Click Manual Deploy -> Deploy latest commit.

This app uses SQLite (file app.db). If you want persistent storage across deploys,
mount a Render Disk and set DB_PATH to a path on the disk, e.g. /var/data/app.db
