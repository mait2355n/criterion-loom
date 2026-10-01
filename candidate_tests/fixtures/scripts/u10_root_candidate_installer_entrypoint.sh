#!/bin/sh -p
set -efu

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
  SEMANTIC_GUARD_U10_INSTALL_LAUNCH=fixed-root-installer-wrapper-v2 \
  "$effective_python" -I -S -B \
  "/Library/Application Support/semantic-guard/u10/bootstrap/prepare_u10_root_candidate.py" \
  install "$@"
