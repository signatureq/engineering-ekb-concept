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
if [[ -f server/.filament-active ]]; then
  compose=(docker compose -p orion -f server/compose.filament.yaml -f server/compose.edge.yaml)
  backend=filament
else
  compose=(docker compose -p orion -f server/compose.yaml -f server/compose.edge.yaml)
  backend=django
fi
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
container_dir="/data/backups/$stamp"
pending="$backup_root/.pending-$stamp"
mkdir "$pending"
if [[ "$backend" == filament ]]; then
  "${compose[@]}" exec -T cms sh -c 'mkdir -p /data/backups && chmod 700 /data/backups'
  "${compose[@]}" exec -T cms php cms/artisan cms:backup --output="$container_dir"
else
  "${compose[@]}" exec -T cms python server/manage.py backup_cms --output "$container_dir"
fi
"${compose[@]}" cp "cms:$container_dir/." "$pending/"
cp server/.env "$pending/deployment.env"
if [[ "$backend" == filament ]]; then
  cp server/.env.filament "$pending/filament.env"
  chmod 600 "$pending/filament.env"
fi
chmod 600 "$pending/cms.sqlite3" "$pending/deployment.env"
mv "$pending" "$backup_root/$stamp"
"${compose[@]}" exec -T cms python -c 'import shutil, sys; shutil.rmtree(sys.argv[1])' "$container_dir"
find "$backup_root" -mindepth 1 -maxdepth 1 -type d -name '20??????T??????Z' -mtime +14 -exec rm -rf -- {} +
printf 'Private backup completed: %s\n' "$stamp"
