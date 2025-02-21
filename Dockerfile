FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей для PostgreSQL-клиента (если нужно) и pip
RUN apt-get update && apt-get install -y postgresql-client

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "bot/bot.py"]
