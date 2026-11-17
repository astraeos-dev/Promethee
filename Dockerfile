# Prométhée : stock de composants et fiches techniques en 3D.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PROMETHEE_FICHES=/donnees/fiches \
    PROMETHEE_DATA=/donnees/base \
    PROMETHEE_EXEMPLES=/app/exemples

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
# Fiches d'exemple, copiées dans /donnees/fiches au premier démarrage si le dossier est vide.
COPY fiches ./exemples

RUN useradd --uid 1000 --create-home promethee \
 && mkdir -p /donnees/fiches /donnees/base \
 && chown -R promethee:promethee /donnees
USER promethee

VOLUME ["/donnees/fiches", "/donnees/base"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/sante', timeout=4)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
