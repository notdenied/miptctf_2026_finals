FROM php:8.3-fpm

# System dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev libpng-dev libzip-dev libfreetype6-dev libjpeg62-turbo-dev libonig-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install pdo pdo_pgsql mbstring gd zip \
    && rm -rf /var/lib/apt/lists/*

# Composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# Install PHP dependencies
COPY composer.json composer.lock* ./
RUN composer install --no-dev --no-scripts --no-interaction --optimize-autoloader || \
    composer install --no-dev --no-interaction --optimize-autoloader

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p /var/www/html/storage/pdfs /tmp/mpdf \
    && chown -R www-data:www-data /var/www/html/storage /tmp/mpdf

# Entrypoint runs both PHP-FPM and built-in server for internal access
RUN chmod +x /var/www/html/entrypoint.sh

EXPOSE 9000 8000

ENTRYPOINT ["/var/www/html/entrypoint.sh"]
