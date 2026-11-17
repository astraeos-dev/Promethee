# Promethee: electronic component inventory and device sheets with a 3D view.
FROM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/astraeos-dev/Promethee" \
      org.opencontainers.image.description="Electronic component inventory and device sheets with a 3D view" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PROMETHEE_SHEETS_DIR=/var/lib/promethee/sheets \
    PROMETHEE_DB_DIR=/var/lib/promethee/db \
    PROMETHEE_EXAMPLES_DIR=/app/examples

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
# Example sheets, copied into the sheets directory on first start when it is empty.
COPY sheets ./examples

COPY docker-entrypoint.sh /usr/local/bin/
RUN useradd --uid 1000 --create-home promethee \
 && mkdir -p /var/lib/promethee/sheets /var/lib/promethee/db \
 && chown -R promethee:promethee /var/lib/promethee

VOLUME ["/var/lib/promethee/sheets", "/var/lib/promethee/db"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
