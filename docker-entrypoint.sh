#!/bin/sh
# When started as root (Home Assistant add-on, docker run without --user),
# prepare the data directories, then drop privileges. Otherwise run as is.
set -e
if [ "$(id -u)" = "0" ]; then
  mkdir -p "$PROMETHEE_SHEETS_DIR" "$PROMETHEE_DB_DIR"
  chown -R promethee:promethee "$PROMETHEE_SHEETS_DIR" "$PROMETHEE_DB_DIR"
  exec setpriv --reuid=promethee --regid=promethee --init-groups "$@"
fi
exec "$@"
