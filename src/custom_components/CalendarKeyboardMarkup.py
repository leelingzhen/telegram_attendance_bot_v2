from calendar import Calendar, month_name
from dataclasses import dataclass
from datetime import date
from typing import List, Tuple

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
    def build(cls, year: int | None = None, month: int | None = None) -> InlineKeyboardMarkup:
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
                row.append(InlineKeyboardButton(str(day.day), callback_data=callback))
            keyboard.append(row)

        prev_year, prev_month = cls._step_month(year, month, -1)
        next_year, next_month = cls._step_month(year, month, 1)

        keyboard.append(
            [
                InlineKeyboardButton(
                    "◀️", callback_data=cls.encode_step(prev_year, prev_month)
                ),
                InlineKeyboardButton(" ", callback_data="noop"),
                InlineKeyboardButton(
                    "▶️", callback_data=cls.encode_step(next_year, next_month)
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
