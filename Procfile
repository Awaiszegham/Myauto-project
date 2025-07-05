web: gunicorn main:app --bind 0.0.0.0:$PORT --workers 2 --worker-class gevent --timeout 120 --keep-alive 2
worker: celery -A src.celery_app.celery worker --loglevel=info --concurrency=2
beat: celery -A src.celery_app.celery beat --loglevel=info
