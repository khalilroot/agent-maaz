FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir eval_type_backport

COPY apps ./apps
COPY AGENTS.md README.md ./

RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

CMD ["uvicorn", "apps.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
