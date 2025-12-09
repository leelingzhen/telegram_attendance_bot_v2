from datetime import datetime, timedelta

from models.enums import AccessCategory
from models.models import Event


def test_event_start_after_end_reflows_end_time():
    start = datetime(2024, 5, 10, 18, 0)
    event = Event(
        id=1,
        title="Test",
        start=start,
        end=start + timedelta(hours=1),
        attendance_deadline=None,
        is_accountable=False,
        access_category=AccessCategory.PUBLIC,
    )

    event.end = start  # ensure end is earlier than the next assignment
    event.start = start + timedelta(hours=4)

    assert event.end == event.start + timedelta(hours=2)


def test_event_start_before_deadline_clears_deadline():
    start = datetime(2024, 5, 10, 18, 0)
    deadline = datetime(2024, 5, 9, 23, 59)
    event = Event(
        id=1,
        title="Test",
        start=start,
        end=start + timedelta(hours=1),
        attendance_deadline=deadline,
        is_accountable=False,
        access_category=AccessCategory.PUBLIC,
    )

    event.start = datetime(2024, 5, 9, 10, 0)

    assert event.attendance_deadline is None
