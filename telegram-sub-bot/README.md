# Telegram Subscription Bot

Telegram-бот с проверкой подписок на каналы и управлением доступом через промокоды.

## Features

- Hourly subscription check for Telegram channels
- Promo code based access management
- Admin panel via Telegram commands
- User notification on unsubscription
- Broadcast messaging to all users
- Statistics dashboard

## Tech Stack

- Python 3.12
- [aiogram 3](https://docs.aiogram.dev/) — Async Telegram Bot framework
- [SQLAlchemy 2.0](https://www.sqlalchemy.org/) — ORM (async)
- [APScheduler](https://apscheduler.readthedocs.io/) — Task scheduling
- Database: SQLite (dev) / PostgreSQL (production)

## Project Structure

```
telegram-sub-bot/
├── Dockerfile
├── railway.json
├── requirements.txt
├── .env.example
├── README.md
└── bot/
    ├── main.py              # Entry point
    ├── config.py            # Environment configuration
    ├── db/
    │   ├── database.py      # Async engine & session
    │   └── models.py        # SQLAlchemy models
    ├── handlers/
    │   ├── user.py          # User commands
    │   └── admin.py         # Admin commands
    ├── middlewares/
    │   └── admin.py         # Admin access middleware
    ├── services/
    │   ├── promo_service.py        # Promo code logic
    │   └── subscription_checker.py # Hourly subscription check
    └── utils/
        └── helpers.py       # Utility functions
```

## Commands

### User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and register |
| `/help` | Show help message |
| `/commands` | List all available commands |
| `/code <code>` | Activate a promo code |
| `/status` | Check your subscription status |
| `/my_channels` | List your subscribed channels |

### Admin Commands

| Command | Description |
|---------|-------------|
| `/add_code <code> <ttl> <channels>` | Create a promo code (e.g. `/add_code PROMO7 7d @ch1,@ch2`) |
| `/codes` | List all promo codes |
| `/revoke_code <code>` | Deactivate a promo code |
| `/add_channel <code> <channel>` | Add a channel to an existing code |
| `/admin_stats` | View bot statistics |
| `/broadcast <message>` | Send a message to all users |

**TTL format:** `30m` (minutes), `24h` (hours), `7d` (days), `2w` (weeks)

## Setup

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/telegram-sub-bot.git
   cd telegram-sub-bot
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate   # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your values:
   ```
   BOT_TOKEN=your_bot_token_here
   DATABASE_URL=sqlite:///bot.db
   ADMIN_IDS=123456789,987654321
   ```

5. **Run the bot:**
   ```bash
   python -m bot.main
   ```

### Creating a Bot via BotFather

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the API token
4. Set bot commands (optional):
   ```
   /setcommands
   ```
   Use the list from the Commands section above.

### Adding Bot to Channels

1. Add the bot as an administrator to each channel
2. Give it at least the "Check members" permission
3. Use the channel's @username (or ID) when creating promo codes

## Deployment on Railway

### Option 1: One-click Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template)

### Option 2: Manual Deploy

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/telegram-sub-bot.git
   git push -u origin main
   ```

2. **Create a Railway project:**
   - Go to [Railway](https://railway.app/)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect the Dockerfile

3. **Set environment variables in Railway:**
   - `BOT_TOKEN` — your bot token
   - `DATABASE_URL` — PostgreSQL connection string (Railway provides this automatically if you add a PostgreSQL plugin)
   - `ADMIN_IDS` — comma-separated Telegram user IDs

4. **Add PostgreSQL plugin:**
   - In Railway dashboard, click "New" → "Database" → "Add PostgreSQL"
   - The `DATABASE_URL` variable is automatically injected

### Railway Configuration

The project includes:
- `Dockerfile` — multi-stage Python build
- `railway.json` — restart policy config

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `BOT_TOKEN` | Yes | Telegram Bot API token | — |
| `DATABASE_URL` | No | Database connection string | `sqlite:///bot.db` |
| `ADMIN_IDS` | Yes | Comma-separated Telegram user IDs | — |

## Database

Supports both SQLite and PostgreSQL:

- **SQLite** (default): `sqlite:///bot.db` — no setup required
- **PostgreSQL** (recommended for production): `postgresql://user:pass@host:5432/dbname`

Tables:
- `users` — Telegram users
- `promo_codes` — Promo codes with channels, TTL, usage limits
- `subscriptions` — User-channel subscriptions
- `events` — Activity log

## Subscription Check

The bot checks every 60 minutes if users are still subscribed to their channels. When an unsubscription is detected:
1. The user receives a notification
2. All admins receive a notification
3. The event is logged in the database

## Possible Improvements

- **Rate limiting**: Add `aiogram` throttling middleware to prevent spam
- **Redis**: Use Redis for FSM storage and caching (instead of MemoryStorage)
- **Database connection pooling**: Fine-tune SQLAlchemy pool settings for high load
- **Batch broadcast**: Use asyncio semaphore for rate-limited message sending
- **Channel ID resolution**: Automatically resolve channel @usernames to chat IDs
- **Webhook mode**: Switch from polling to webhook for production
- **Metrics**: Add Prometheus metrics for monitoring
- **i18n**: Multi-language support
- **Admin panel UI**: Web-based admin interface
- **Subscription expiry**: Auto-remove access when promo code expires
