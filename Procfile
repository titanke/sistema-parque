web: gunicorn posApp.wsgi --log-file -
web: python manage.py migrate && gunicorn post posApp.wsgi
