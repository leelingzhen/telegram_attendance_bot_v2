# Telegram Attendance Bot

A Telegram bot for managing attendance at events and training sessions.

## Project Structure

See `src/README.md` for detailed information about the project structure and architecture.

## Development

### Local Development
1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e "src/.[dev]"
```

3. Create a `.env` file in the root directory with the following variables:
```env
# Telegram Bot Token (get from @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=attendance_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# Optional: Logging Configuration
LOG_LEVEL=INFO
```

4. Run the bot:
```bash
# 1. running the file directly from root directory
python src/main.py
# or 
python -m src.main

# 2. run the the package installer at step 2 and you can use the command line 
attendance-bot
```

## Environment Variables

### Required
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from @BotFather

### Database (Required for production)
- `DB_HOST`: Database host
- `DB_PORT`: Database port
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password

### Optional
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Development

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run tests:
```bash
pytest
```

## License

[Your License Here] 
