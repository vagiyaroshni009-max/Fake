"""PythonAnywhere WSGI template.
Update <your_pythonanywhere_username> and <your_repo_folder> before use.
"""
import sys
from pathlib import Path

project_home = Path('/home/<your_pythonanywhere_username>/<your_repo_folder>')
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

from app import app as application
