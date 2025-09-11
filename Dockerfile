FROM python:3.12-slim

# Ishchi papka
WORKDIR /app

# requirements.txt ni o‘rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app fayllarni ko‘chirish
COPY app/ ./app/

# Botni ishga tushirish
CMD ["python", "app/main.py"]