FROM python:3.12

WORKDIR /app

COPY bot/bot.py /app/bot/
COPY . /app


COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["python3", "/app/bot/bot.py"]
