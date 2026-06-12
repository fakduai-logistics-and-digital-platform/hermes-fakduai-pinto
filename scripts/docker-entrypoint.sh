#!/usr/bin/env sh
set -eu

HERMES_HOME="${HERMES_HOME:-/root/.hermes}"
PLUGIN_SRC="${PLUGIN_SRC:-/opt/hermes-pinto-plugin}"
PLUGIN_DEST="${HERMES_HOME}/plugins/platforms/pinto"

# ── Install plugin files ──
if [ ! -f "${PLUGIN_DEST}/adapter.py" ]; then
  echo "Installing Pinto plugin to ${PLUGIN_DEST}"
  mkdir -p "${PLUGIN_DEST}"
  cp "${PLUGIN_SRC}/adapter.py"    "${PLUGIN_DEST}/adapter.py"
  cp "${PLUGIN_SRC}/plugin.yaml"   "${PLUGIN_DEST}/plugin.yaml"
  cp "${PLUGIN_SRC}/__init__.py"   "${PLUGIN_DEST}/__init__.py"
else
  echo "Pinto plugin already installed at ${PLUGIN_DEST}"
fi

# ── Bootstrap config ──
python3 /usr/local/bin/bootstrap-hermes-config.py

exec "$@"
