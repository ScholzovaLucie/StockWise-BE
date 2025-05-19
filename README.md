# 🏗️ StockWise – Backend

Tento repozitář obsahuje backendovou část systému StockWise pro správu skladů. Backend je postaven na frameworku **Django 4.2** s využitím **Django REST Framework**, **PostgreSQL**, **JWT autentizace**, a napojením na **OpenAI GPT-4o** pro inteligentního chatbota a statistiky.

---

## 🔧 Použité technologie

- Python 3.11
- Django 4.2
- Django REST Framework
- PostgreSQL (Supabase nebo Docker)
- JWT autentizace (`SimpleJWT`)
- Swagger dokumentace (`drf-yasg`)
- OpenAI GPT-4o (přes API)
- Docker + Gunicorn

---

## 📝 .env (příklad)
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

DB_USER=postgres.etcoksjerwplaibvjtjt
DB_PASSWORD=Noidlevinedowney12+
DB_HOST=aws-0-eu-west-2.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres

TESTING=0
```

---

## ⚙️ Lokální spuštění (Docker)

Ujisti se, že máš nainstalovaný Docker a Docker Compose.

```bash
docker-compose up --build
```

---

## 🔐 Autentizace
Backend používá JWT tokeny uložené v cookies (HttpOnly, Secure, SameSite=None). K dispozici jsou tyto endpointy:

---

## 📚 Dokumentace API
- Swagger UI: http://localhost:8000/swagger/
- oc: http://localhost:8000/redoc/