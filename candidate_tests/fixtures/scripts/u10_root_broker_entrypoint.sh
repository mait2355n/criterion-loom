#!/bin/sh -p
set -efu

if [ "$#" -ne 6 ]; then
  echo "U-10 broker entrypoint requires exactly six request arguments" >&2
  exit 64
fi

effective_python_path_file='/Library/Application Support/semantic-guard/u10/bootstrap/effective-python.path'
effective_python=''
exec 3< "$effective_python_path_file" || {
  echo "U-10 effective Python path is unreadable" >&2
  exit 70
}
IFS= read -r effective_python <&3 || {
  echo "U-10 effective Python path is unreadable" >&2
  exit 70
}
case "$effective_python" in
  /*) ;;
  *)
    echo "U-10 effective Python path is not absolute" >&2
    exit 70
    ;;
esac
if [ -z "$effective_python" ] || IFS= read -r _unexpected_second_line <&3; then
  echo "U-10 effective Python path must contain exactly one line" >&2
  exit 70
fi
exec 3<&-

exec /usr/bin/env -i \
  PATH= \
  LC_ALL=C \
  PYTHONDONTWRITEBYTECODE=1 \
  SEMANTIC_GUARD_U10_LAUNCH=fixed-root-wrapper-v3 \
  "$effective_python" -I -S -B \
  "/Library/Application Support/semantic-guard/u10/bootstrap/u10_root_broker_outer_launcher.py" \
  "$@"
