#!/bin/sh -p
set -efu

if [ "$#" -ne 2 ]; then
  echo "U-10 root control entrypoint requires OPERATION IDENTIFIER" >&2
  exit 64
fi

case "$1" in
  activate-snapshot|activate-store|key|project-snapshot|revoke-store) ;;
  *)
    echo "U-10 root control operation is not allowed" >&2
    exit 64
    ;;
esac

case "$2" in
  ''|*[!A-Za-z0-9._-]*)
    echo "U-10 root control identifier is invalid" >&2
    exit 64
    ;;
esac

effective_python_path_file='/Library/Application Support/semantic-guard/u10/bootstrap/effective-python.path'
effective_python=''
exec 3< "$effective_python_path_file" || {
  echo "U-10 broker Python path is unreadable" >&2
  exit 70
}
IFS= read -r effective_python <&3 || {
  echo "U-10 broker Python path is unreadable" >&2
  exit 70
}
case "$effective_python" in
  /*) ;;
  *)
    echo "U-10 broker Python path is not absolute" >&2
    exit 70
    ;;
esac
if [ -z "$effective_python" ] || IFS= read -r _unexpected_second_line <&3; then
  echo "U-10 broker Python path must contain exactly one line" >&2
  exit 70
fi
exec 3<&-

exec /usr/bin/env -i \
  PATH= \
  LC_ALL=C \
  PYTHONDONTWRITEBYTECODE=1 \
  SEMANTIC_GUARD_U10_CONTROL_LAUNCH=fixed-root-control-wrapper-v1 \
  "$effective_python" -I -S -B \
  "/Library/Application Support/semantic-guard/u10/bootstrap/u10_root_control_outer_launcher.py" \
  "$@"
