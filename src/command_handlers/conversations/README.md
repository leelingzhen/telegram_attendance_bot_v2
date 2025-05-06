# Conversations Directory

This directory contains conversation flow handlers for different bot interactions.

## Files

- `conversation_flow.py`: Abstract base class for all conversation flows
- `attendance_conversation.py`: Handles attendance marking conversation
- `view_attendance_conversation.py`: Handles viewing attendance conversation
- `manage_attendance_conversation.py`: Handles managing attendance conversation
- `manage_events_conversation.py`: Handles event management conversation
- `manage_users_conversation.py`: Handles user management conversation

## Overview

The conversation layer is responsible for:
1. Managing user interaction flows
2. Handling state transitions
3. Processing user input
4. Providing appropriate responses

## Architecture

Each conversation follows this pattern:
```
ConversationFlow (abstract)
  ├─ State Definitions
  ├─ Conversation Handler
  │   ├─ Entry Points
  │   ├─ State Handlers
  │   └─ Fallbacks
  └─ Provider Dependencies
      └─ Specific Provider Interface
```

## Usage

Conversations are used by the bot layer to handle specific user interactions:

```python
provider = AttendanceProviderImpl(service)
conversation = MarkAttendanceConversation(provider)
bot.add_handler(conversation.conversation_handler)
```

## Testing

Conversations can be tested using mock providers:

```python
mock_provider = MockAttendanceProvider()
conversation = MarkAttendanceConversation(mock_provider)
# Test conversation flow
``` 