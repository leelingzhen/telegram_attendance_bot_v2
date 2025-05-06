# Source Directory

This directory contains the main source code for the Telegram Attendance Bot.

## Directory Structure

- `bots/`: Core bot implementations and handlers
- `conversations/`: Conversation flow handlers for different bot interactions
- `models/`: Data models and database schemas
- `providers/`: Service providers that abstract data access
- `services/`: Base service implementations for data operations

## Overview

The application follows a layered architecture:

1. **Bot Layer** (`bots/`): Handles Telegram bot initialization and high-level flow
2. **Conversation Layer** (`conversations/`): Manages user interaction flows
3. **Provider Layer** (`providers/`): Abstracts data access for specific features
4. **Service Layer** (`services/`): Implements core data operations
5. **Model Layer** (`models/`): Defines data structures and schemas

Each layer has a specific responsibility and communicates with adjacent layers through well-defined interfaces. 