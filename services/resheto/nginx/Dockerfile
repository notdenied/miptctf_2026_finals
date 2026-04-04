FROM nginx:1.25-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/ /var/www/html/

EXPOSE 8888
