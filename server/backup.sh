#!/usr/bin/env bash
set -euo pipefail
umask 077

project_dir="${ORION_PROJECT_DIR:-/opt/orion/site}"
backup_root="${ORION_BACKUP_DIR:-/var/backups/orion}"
mkdir -p "$backup_root"
chmod 700 "$backup_root"
exec 9>"$backup_root/.lock"
flock -n 9 || exit 0

cd "$project_dir"
compose=(docker compose -p orion -f server/compose.yaml -f server/compose.edge.yaml)
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
container_dir="/data/backups/$stamp"
pending="$backup_root/.pending-$stamp"
mkdir "$pending"
"${compose[@]}" exec -T cms python server/manage.py backup_cms --output "$container_dir"
"${compose[@]}" cp "cms:$container_dir/." "$pending/"
cp server/.env "$pending/deployment.env"
chmod 600 "$pending/cms.sqlite3" "$pending/deployment.env"
mv "$pending" "$backup_root/$stamp"
"${compose[@]}" exec -T cms python -c 'import shutil, sys; shutil.rmtree(sys.argv[1])' "$container_dir"
find "$backup_root" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -mtime +14 -exec rm -rf -- {} +
printf 'Private backup completed: %s\n' "$stamp"
