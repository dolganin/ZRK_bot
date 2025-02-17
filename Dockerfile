FROM python:3.12

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем только файл с зависимостями
COPY requirements.txt /app/

# Устанавливаем зависимости ДО копирования остального кода (используем кэш)
RUN pip install --no-cache-dir -r requirements.txt

# Копируем оставшийся код проекта
COPY . /app

# Запускаем бота
CMD ["python3", "bot/bot.py"]
