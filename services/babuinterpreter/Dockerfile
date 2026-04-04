FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV BABUIN_SERVICE_PORT=31337
ENV BABUIN_STORAGE_PATH=/var/lib/babuinterpreter/storage.sqlite

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        socat \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --home-dir /home/babuinterpreter --shell /usr/sbin/nologin babuinterpreter \
    && mkdir -p /var/lib/babuinterpreter \
    && mkdir -p /service \
    && chown -R babuinterpreter:babuinterpreter /var/lib/babuinterpreter /service

COPY babuinterpreter /service/babuinterpreter
COPY entrypoint.py /service/entrypoint.py
COPY start.sh /service/start.sh

RUN chmod 0755 /service/babuinterpreter /service/entrypoint.py /service/start.sh \
    && chown babuinterpreter:babuinterpreter /service/babuinterpreter /service/entrypoint.py /service/start.sh

EXPOSE 31337

CMD ["/service/start.sh"]
