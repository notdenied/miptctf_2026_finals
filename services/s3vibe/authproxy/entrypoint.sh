if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    echo "Generated new SECRET_KEY: ${SECRET_KEY:0:20}...${SECRET_KEY: -10}"
else
    echo "Using provided SECRET_KEY"
fi

exec python server.py