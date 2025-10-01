# Imagen base ligera
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias
COPY requirements/base.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar el proyecto
COPY . .

# Recopilar estáticos (producción)
RUN python manage.py collectstatic --noinput

# Exponer puerto
EXPOSE 8000

# Ejecutar migraciones automáticamente al arrancar y luego iniciar Gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2 --timeout 120"]
