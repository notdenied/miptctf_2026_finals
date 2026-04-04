#!/bin/bash
set -e

# Start PHP built-in server for internal access (worker calls this)
php -S 0.0.0.0:8000 -t /var/www/html/public /var/www/html/public/index.php &

# Start PHP-FPM in foreground (nginx proxies to this)
exec php-fpm --nodaemonize
