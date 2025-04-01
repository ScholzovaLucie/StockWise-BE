# Použití Python 3.11
FROM python:3.11

COPY ./entrypoint.sh /

# Nastavení pracovního adresáře
WORKDIR /

# Kopírování requirements.txt
COPY requirements.txt /requirements.txt

# Instalace závislostí
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    TZ="Europe/Prague"

# Kopírování zdrojového kódu
COPY . .

# Exponování portu 8000
EXPOSE 8000

# Spuštění Django serveru
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]