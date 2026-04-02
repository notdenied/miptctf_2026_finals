FROM python:3.9-alpine

WORKDIR /app

COPY templates ./templates
COPY app.py app.py
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

CMD [ "python3","app.py" ]