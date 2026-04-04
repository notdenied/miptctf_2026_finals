FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV BABUIN_SERVICE_PORT=31337
ENV BABUIN_STORAGE_PATH=/var/lib/babuinterpreter/storage.sqlite

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        socat \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/lib/babuinterpreter
RUN mkdir -p /service

COPY babuinterpreter /service/babuinterpreter
COPY entrypoint.py /service/entrypoint.py

RUN chmod 0755 /service/babuinterpreter /service/entrypoint.py

EXPOSE 31337

CMD ["sh", "-c", "port=\"${BABUIN_SERVICE_PORT:-31337}\"; exec socat \"TCP-LISTEN:${port},reuseaddr,fork\" EXEC:/service/entrypoint.py,stderr"]
