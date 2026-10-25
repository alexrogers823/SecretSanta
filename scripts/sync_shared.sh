#!/bin/sh
# Cloud Run and Cloud Functions only upload their own folder, so copy shared/ into
# each one before deploying. Locally, flask_server finds ../shared through PYTHONPATH
# (see flask_server/.env.example), so delete these copies after deploying.
set -e
root="$(cd "$(dirname "$0")/.." && pwd)"
for target in flask_server functions; do
  [ -d "$root/$target" ] || continue
  rm -rf "$root/$target/shared"
  cp -R "$root/shared" "$root/$target/shared"
  rm -rf "$root/$target/shared/__pycache__"
done
