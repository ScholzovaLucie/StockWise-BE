# Použití Python 3.11
FROM python:3.11

# Nastavení pracovního adresáře
WORKDIR /app

# Kopírování requirements.txt
COPY requirements.txt /app/requirements.txt

# Instalace závislostí
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# Kopírování zdrojového kódu
COPY . .

# Exponování portu 8000
EXPOSE 8000

# Spuštění Django serveru
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]