from datetime import date

from custom_components.CalendarKeyboardMarkup import CalendarKeyboardMarkup


def test_calendar_build_includes_navigation_and_days():
    markup = CalendarKeyboardMarkup.build(year=2024, month=2)

    keyboard = markup.inline_keyboard
    assert keyboard[0][0].text == "February 2024"

    day_buttons = [
        button
        for row in keyboard[2:-1]
        for button in row
        if button.callback_data.startswith(CalendarKeyboardMarkup.callback_data.date_prefix)
    ]
    assert len(day_buttons) == 29
    assert day_buttons[0].text == "1"

    prev_button, _, next_button = keyboard[-1]
    assert prev_button.callback_data == "step:2024-01"
    assert next_button.callback_data == "step:2024-03"


def test_calendar_callbacks_decode():
    test_date = date(2025, 12, 9)
    encoded_date = CalendarKeyboardMarkup.encode_date(test_date)
    assert CalendarKeyboardMarkup.parse_date(encoded_date) == test_date

    encoded_step = CalendarKeyboardMarkup.encode_step(2025, 11)
    assert CalendarKeyboardMarkup.parse_step(encoded_step) == (2025, 11)
