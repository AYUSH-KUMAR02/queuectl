import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))   # Read .env file

SECRET_KEY = env('my_django_key')

DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'queue_manager.apps.QueueManagerConfig',
]

MIDDLEWARE = []

ROOT_URLCONF = 'queuectl.urls'

TEMPLATES = []

WSGI_APPLICATION = 'queuectl.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
	'NAME': BASE_DIR / env('DB_NAME', default='db.sqlite3'),
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'