FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y lighttpd && \
    rm -rf /var/lib/apt/lists/*

# Enable mod_proxy
RUN lighttpd-enable-mod proxy

COPY lighttpd.conf /etc/lighttpd/lighttpd.conf

EXPOSE 8080

CMD ["lighttpd", "-D", "-f", "/etc/lighttpd/lighttpd.conf"]
