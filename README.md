# 🌟 Sardoba Review Telegram Bot  

A Telegram bot for collecting **reviews and ratings** of branches.  
Users can leave **1–5 star ratings**, write feedback, and optionally attach photos.  
Admins and Super Admins manage reviews, ratings, and statistics directly inside Telegram.  

---

## ✨ Features  
- 🇺🇿 Uzbek / 🇷🇺 Russian multilingual support  
- Users: rate branches (1–5 ⭐), write reviews, attach photos  
- Admins: view statistics (avg rating, number of reviews per branch)  
- Super Admins: manage admins and branches  
- Built with **Aiogram 3 + PostgreSQL + SQLAlchemy**  
- Dockerized for quick VPS deployment (Eskiz friendly)  

---

## 🛠 Tech Stack  
- **Python 3.12**  
- **Aiogram 3.13**  
- **PostgreSQL 15**  
- **SQLAlchemy 2.0**  
- **Docker & Docker Compose**  

---

## 📂 Project Structure  

```bash
reviewbot/
├─ docker-compose.yml
├─ Dockerfile
├─ .env.example
├─ README.md
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ keyboards.py
│  ├─ middlewares.py
│  ├─ i18n.py
│  ├─ locales/
│  │  ├─ uz.json
│  │  └─ ru.json
│  ├─ db/
│  │  ├─ session.py
│  │  ├─ models.py
│  │  ├─ crud.py
│  │  └─ init.sql
│  └─ handlers/
│     ├─ user.py
│     └─ admin.py
└─ requirements.txt
```

---

## ⚙️ Setup & Run  

### 1. Clone repository  
```bash
git clone git@github.com:abdurakhmonovsharif/sardoba-review-telegram-bot.git
cd sardoba-review-telegram-bot
```

### 2. Configure environment

Copy .env.example → .env and fill:

```dotenv
BOT_TOKEN=123456:ABC-YourTokenHere
POSTGRES_USER=review
POSTGRES_PASSWORD=reviewpass
POSTGRES_DB=reviewdb
DATABASE_URL=postgresql+asyncpg://review:reviewpass@db:5432/reviewdb
SUPER_ADMINS=123456789
REVIEW_GROUP_BATCH_ENABLED=false
REVIEW_GROUP_BATCH_SIZE=10
```

`REVIEW_GROUP_BATCH_ENABLED=false` keeps the current behavior and sends each
review to the configured group immediately. Set it to `true` to send the
oldest 10 unsent reviews together after the tenth review arrives. The batch
size can be changed with `REVIEW_GROUP_BATCH_SIZE`.

### 3. Run with Docker

```bash
docker compose up -d --build
```

After changing `.env`, run the same command to recreate the bot container.

### 4. Interact with the bot

- Send `/start` → choose language → register → leave a review
- Admins use `/admin_sardoba` → view statistics

⸻

📊 Example Admin Statistics

🏢 Buxoro – 5-mikrorayon, Piridasgir ko‘chasi, Mega bozori yonida — 12 reviews, ⭐ 4.6  
🏢 Buxoro – Dilkusho ko‘chasi, 2B-uy — 8 reviews, ⭐ 4.3  
🏢 Kogon – Kogoncha shosse, Kalinin burilishi — 15 reviews, ⭐ 4.6


⸻

📜 License

MIT License © 2025 Sharif Abdurakhmonov
