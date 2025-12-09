from calendar import Calendar, month_name, monthrange
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


@dataclass(frozen=True)
class CalendarCallbackData:
    date_prefix: str = "date:"
    step_prefix: str = "step:"


class CalendarKeyboardMarkup:
    """
    Calendar date picker inline keyboard.

    - Opens directly in month view.
    - Supports previous/next month navigation.
    - Emits callback data of the form `date:YYYY-MM-DD` for selections and
      `step:YYYY-MM` for navigation.
    """

    callback_data = CalendarCallbackData()

    @classmethod
    def build(
        cls,
        year: int | None = None,
        month: int | None = None,
        *,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> InlineKeyboardMarkup:
        today = date.today()
        year = year or today.year
        month = month or today.month

        cal = Calendar(firstweekday=0)
        month_days = cal.monthdatescalendar(year, month)

        keyboard: List[List[InlineKeyboardButton]] = []

        # Header row with month and year label
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{month_name[month]} {year}", callback_data="noop"
                )
            ]
        )

        # Weekday headers (Mon-Sun)
        weekday_labels = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        keyboard.append([
            InlineKeyboardButton(day, callback_data="noop") for day in weekday_labels
        ])

        for week in month_days:
            row: List[InlineKeyboardButton] = []
            for day in week:
                if day.month != month:
                    row.append(InlineKeyboardButton(" ", callback_data="noop"))
                    continue

                callback = cls.encode_date(day)
                is_disabled = (start_date and day < start_date) or (end_date and day > end_date)
                cb_data = "noop" if is_disabled else callback
                label = " " if is_disabled else str(day.day)
                row.append(InlineKeyboardButton(label, callback_data=cb_data))
            keyboard.append(row)

        prev_year, prev_month = cls._step_month(year, month, -1)
        next_year, next_month = cls._step_month(year, month, 1)
        prev_enabled = cls._month_within_range(prev_year, prev_month, start_date, end_date)
        next_enabled = cls._month_within_range(next_year, next_month, start_date, end_date)

        keyboard.append(
            [
                InlineKeyboardButton(
                    "◀️" if prev_enabled else " ",
                    callback_data=cls.encode_step(prev_year, prev_month) if prev_enabled else "noop",
                ),
                InlineKeyboardButton(" ", callback_data="noop"),
                InlineKeyboardButton(
                    "▶️" if next_enabled else " ",
                    callback_data=cls.encode_step(next_year, next_month) if next_enabled else "noop",
                ),
            ]
        )

        return InlineKeyboardMarkup(keyboard)

    @classmethod
    def encode_date(cls, day: date) -> str:
        return f"{cls.callback_data.date_prefix}{day.strftime('%Y-%m-%d')}"

    @classmethod
    def encode_step(cls, year: int, month: int) -> str:
        return f"{cls.callback_data.step_prefix}{year:04d}-{month:02d}"

    @classmethod
    def parse_date(cls, data: str) -> date:
        if not data.startswith(cls.callback_data.date_prefix):
            raise ValueError("Not a calendar date callback")
        return date.fromisoformat(data.removeprefix(cls.callback_data.date_prefix))

    @classmethod
    def parse_step(cls, data: str) -> Tuple[int, int]:
        if not data.startswith(cls.callback_data.step_prefix):
            raise ValueError("Not a calendar step callback")
        step_payload = data.removeprefix(cls.callback_data.step_prefix)
        year_str, month_str = step_payload.split("-")
        return int(year_str), int(month_str)

    @staticmethod
    def _step_month(year: int, month: int, delta: int) -> Tuple[int, int]:
        month += delta
        if month == 0:
            return year - 1, 12
        if month == 13:
            return year + 1, 1
        return year, month

    @staticmethod
    def _month_within_range(
        year: int,
        month: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> bool:
        """
        Return True if the month intersects with the allowed range.
        """
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        if start_date and last_day < start_date:
            return False
        if end_date and first_day > end_date:
            return False
        return True
