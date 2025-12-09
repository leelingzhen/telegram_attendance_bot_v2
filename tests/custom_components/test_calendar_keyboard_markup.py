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


def test_calendar_respects_date_range_and_disables_navigation():
    start = date(2024, 5, 10)
    end = date(2024, 5, 15)
    markup = CalendarKeyboardMarkup.build(year=2024, month=5, start_date=start, end_date=end)
    keyboard = markup.inline_keyboard

    # Find a button that should be disabled (e.g., 1st of the month)
    flattened = [btn for row in keyboard[2:-1] for btn in row]
    first_days = [btn for btn in flattened if btn.text.strip() == "1"]
    assert first_days == []  # hidden when out of range

    # Buttons within range still appear
    in_range = [btn for btn in flattened if btn.text.strip() == "10"]
    assert in_range and in_range[0].callback_data.startswith(CalendarKeyboardMarkup.callback_data.date_prefix)

    # Nav arrows should be disabled when moving outside range
    prev_btn, _, next_btn = keyboard[-1]
    assert prev_btn.text.strip() == ""
    assert prev_btn.callback_data == "noop"
    assert next_btn.text.strip() == ""
    assert next_btn.callback_data == "noop"
