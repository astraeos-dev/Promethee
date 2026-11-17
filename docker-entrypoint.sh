#!/bin/sh
# Démarré en root (Home Assistant, docker run sans --user) : prépare les dossiers
# de données puis abandonne les privilèges. Sinon, lance directement la commande.
set -e
if [ "$(id -u)" = "0" ]; then
  mkdir -p "$PROMETHEE_FICHES" "$PROMETHEE_DATA"
  chown -R promethee:promethee "$PROMETHEE_FICHES" "$PROMETHEE_DATA"
  exec setpriv --reuid=promethee --regid=promethee --init-groups "$@"
fi
exec "$@"
