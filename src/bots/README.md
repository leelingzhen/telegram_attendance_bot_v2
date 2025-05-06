# Bots Directory

This directory contains the core bot implementations and handlers.

## Files

- `bot_core.py`: Base bot implementation with common functionality
- `training_bot.py`: Training-specific bot implementation

## Overview

The bot layer is responsible for:
1. Initializing the Telegram bot
2. Managing service and provider dependencies
3. Setting up conversation handlers
4. Handling the bot lifecycle (start/stop)

## Architecture

```
TrainingBot
  ├─ BotCore (base functionality)
  ├─ Service Dependencies
  │   └─ BaseService
  ├─ Provider Dependencies
  │   └─ AttendanceProvider
  └─ Conversation Handlers
      └─ MarkAttendanceConversation
```

## Usage

The bot layer is the entry point for the application. It should be instantiated with the appropriate service implementation:

```python
service = YourBaseServiceImplementation()
bot = TrainingBot(token="your-token", service=service)
await bot.run()
``` 