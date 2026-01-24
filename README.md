FROM python:3.11-slim

WORKDIR /app

# Копируем requirements.txt первым (для кэширования слоев)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY . .

# Запускаем бота
CMD ["python", "bot.py"]
