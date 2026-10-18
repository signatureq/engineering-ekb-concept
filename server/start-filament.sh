#!/bin/sh
set -eu
mkdir -p /data/media /data/builds /data/backups /data/storage/framework/cache/data /data/storage/framework/sessions /data/storage/framework/views /data/storage/logs
chown -R www-data:www-data /data
chmod 755 /data
cd /app/cms
php artisan migrate --force
chmod 600 /data/cms.sqlite
chmod 700 /data/media /data/storage /data/backups
php artisan config:cache
php artisan view:cache
exec php-fpm
