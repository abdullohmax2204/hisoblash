# 💰 Hisoblash Bot & Telegram Mini App — Personal Finance

Персональный Telegram-бот и интерактивное веб-приложение (**Telegram Mini App**) для полноценного учёта финансов: доходы, расходы, счета, накопления, цели, долги, графики и аналитика.

## Возможности

- 📱 **Telegram Mini App (Web App)** — стильный и современный визуальный интерфейс прямо в Telegram
- 💰 **Доход** — быстрое добавление поступлений по счетам и категориям
- 💸 **Расход** — запись трат с быстрыми чипами сумм и категориями
- 🏦 **Счета и Банк** — мультикарта, наличные, баланс каждого счёта и переводы
- 💵 **Накопления и Цели** — откладывание денег, прогресс-бары целей (например: "На iPhone", "Подушка безопасности")
- 🤝 **Долги** — учёт выданных и взятых долгов с частичным и полным погашением
- 📊 **Статистика и Графика** — интерактивные диаграммы Chart.js за день, неделю, месяц и всё время
- 📜 **История операций** — полный журнал с возможностью отмены/удаления операций и пересчетом баланса

## Требования

- Python 3.12+
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- Ваш Telegram User ID (от [@userinfobot](https://t.me/userinfobot))

## Установка

### 1. Клонировать проект

```bash
git clone <repo-url>
cd Hisoblash_bot
```

### 2. Создать виртуальное окружение

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить окружение

```bash
# Windows
copy .env.example .env

# Linux
cp .env.example .env
```

Заполните `.env`:

```env
BOT_TOKEN=123456:ABC-DEF...        # Токен от @BotFather
ADMIN_USER_ID=987654321             # Ваш Telegram ID от @userinfobot
DATABASE_URL=sqlite+aiosqlite:///./data/finance.db
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 5. Создать базу данных

```bash
mkdir data
alembic upgrade head
```

### 6. Запустить бота

```bash
python -m app
```

Бот начнёт работу. Откройте его в Telegram и отправьте `/start`.

## Тестирование

```bash
pytest
```

## Бэкап базы данных

```bash
python -m app.backup
```

Копия сохраняется в `backups/` с временной меткой.

## Структура проекта

```
app/
├── bot/           # Telegram: handlers, keyboards, FSM, middlewares
├── core/          # Config, logging
├── database/      # SQLAlchemy models, engine
├── repositories/  # Data access layer
├── services/      # Business logic
├── __main__.py    # Entry point
└── backup.py      # Backup utility

alembic/           # Database migrations
tests/             # Pytest tests
deploy/            # systemd service for Linux
```

## Deployment на Linux VPS

### Системные зависимости

```bash
sudo apt update && sudo apt install python3 python3-venv python3-pip
```

### Установка

```bash
sudo mkdir -p /opt/finance-bot
cd /opt/finance-bot
git clone <repo-url> .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
mkdir data
alembic upgrade head
```

### systemd

```bash
sudo cp deploy/finance-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable finance-bot
sudo systemctl start finance-bot
sudo systemctl status finance-bot
```

### Логи

```bash
journalctl -u finance-bot -f
```

### Docker (альтернатива)

```bash
docker compose up -d
```

## Лицензия

Personal use only.
