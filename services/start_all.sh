#!/bin/bash

cd /home/ubuntu/services || exit

for dir in */; do
    if [ -f "$dir/docker-compose.yml" ]; then
        cd "$dir" || exit
        docker compose up -d
        cd ..
    fi
done
