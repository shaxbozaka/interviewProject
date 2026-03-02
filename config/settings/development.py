from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS += [  # noqa: F405
    'debug_toolbar',
    'silk',
]

MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
MIDDLEWARE.append('silk.middleware.SilkyMiddleware')  # noqa: F405

INTERNAL_IPS = ['127.0.0.1']

CORS_ALLOW_ALL_ORIGINS = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SILKY_PYTHON_PROFILER = True
