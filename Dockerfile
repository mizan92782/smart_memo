
# === Base Stage ===

FROM python:3.11 AS base

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .



# === Development Stage ===

FROM base AS development

ENV DEBUG=True

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]




# === Production Stage ===

FROM python:3.11-slim AS production

WORKDIR /app

COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /app /app

ENV DEBUG=False

RUN pip install --no-cache-dir gunicorn celery

CMD ["gunicorn", "smart_memo.wsgi:application", "--bind", "0.0.0.0:8000"]