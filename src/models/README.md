# Models Directory

This directory contains data models and database schemas.

## Files

- `models.py`: Core data models and enums

## Overview

The model layer is responsible for:
1. Defining data structures
2. Enforcing data validation
3. Providing type hints
4. Defining database schemas

## Architecture

Models follow this pattern:
```
Models
  ├─ User
  │   ├─ ID
  │   ├─ Name
  │   └─ Access Category
  ├─ Event
  │   ├─ ID
  │   ├─ Title
  │   ├─ Date
  │   └─ Access Category
  └─ Attendance
      ├─ ID
      ├─ User ID
      ├─ Event ID
      ├─ Status
      └─ Reason
```

## Usage

Models are used throughout the application to represent data:

```python
user = User(
    id=123,
    name="John Doe",
    access_category=AccessCategory.MEMBER
)

event = Event(
    id=1,
    title="Training Session",
    date=date.today(),
    access_category=AccessCategory.MEMBER
)

attendance = Attendance(
    id=0,
    user_id=user.id,
    event_id=event.id,
    status=AttendanceStatus.ATTENDING,
    reason="Will be there"
)
```

## Enums

The models include several enums:
1. `AccessCategory`: Defines user access levels
2. `AttendanceStatus`: Defines possible attendance statuses

## Future Enhancements

Models can be enhanced with:
1. Validation rules
2. Serialization methods
3. Database constraints
4. Migration support
5. Audit fields 