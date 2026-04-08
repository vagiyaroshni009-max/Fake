# Deployment Guide (Render + PythonAnywhere)

This project is now prepared with:
- `requirements.txt`
- `Procfile`
- `runtime.txt`
- production-safe `app.py` startup (`app.run()` only, no `debug=True`)
- DB config using environment variables in `database/db_config.py`

## 1) Required Environment Variables

Set these on your hosting platform:

- `SECRET_KEY`
- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `DB_PORT`

Optional:
- `FLASK_ENV=production`
- `DEBUG=False`

## 2) Render Deployment Steps

1. Push this project to GitHub.
2. Go to Render dashboard and click **New +** -> **Web Service**.
3. Connect your GitHub repository.
4. Environment: **Python**.
5. Build Command:
   - `pip install -r requirements.txt`
6. Start Command:
   - `gunicorn app:app`
7. Add environment variables listed above.
8. Click **Create Web Service**.
9. After deploy completes, open the Render URL.

## 3) PythonAnywhere Deployment Steps

### A) Upload project files

Option 1: Git (recommended)
1. Open a PythonAnywhere Bash console.
2. Run:
   - `git clone <your-github-repo-url>`
3. Enter project:
   - `cd <your-repo-folder>`
4. Install dependencies in a virtualenv:
   - `python3.12 -m venv venv`
   - `source venv/bin/activate`
   - `pip install -r requirements.txt`

Option 2: ZIP upload
1. Zip project locally.
2. Upload in PythonAnywhere **Files** tab.
3. Extract zip in home directory.
4. Create virtualenv and install requirements as above.

### B) Create a Web App

1. In PythonAnywhere dashboard -> **Web** -> **Add a new web app**.
2. Choose **Manual configuration**.
3. Select Python 3.12.
4. Set virtualenv path to your created `venv`.

### C) WSGI Configuration

Edit the WSGI file for your web app and replace with:

```python
import sys
from pathlib import Path

project_home = Path('/home/<your_pythonanywhere_username>/<your_repo_folder>')
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

from app import app as application
```

### D) Environment variables on PythonAnywhere

In **Web** tab, add these in Environment Variables:
- `SECRET_KEY`
- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `DB_PORT`

If using PythonAnywhere MySQL, values are typically:
- `DB_HOST=<username>.mysql.pythonanywhere-services.com`
- `DB_USER=<username>`
- `DB_NAME=<username>$<database_name>`
- `DB_PORT=3306`

### E) Reload

1. Click **Reload** in Web tab.
2. Open your PythonAnywhere app URL.

## 4) Notes

- `Procfile` uses: `web: gunicorn app:app`
- `runtime.txt` uses: `python-3.12.0`
- `requirements.txt` is generated from `pip freeze` and includes `gunicorn`.
