from telegram import MessageEntity

from utils.markup_converter import MessageMarkupConverter


def test_html_to_entities_and_back():
    html = 'Hello <b>World</b> <i>Italic</i> <a href="https://example.com">link</a>'

    text, entities = MessageMarkupConverter.html_to_entities(html)

    assert text == "Hello World Italic link"
    assert {e.type for e in entities} == {
        MessageEntity.BOLD,
        MessageEntity.ITALIC,
        MessageEntity.TEXT_LINK,
    }

    round_trip = MessageMarkupConverter.entities_to_html(text, entities)
    assert "<b>World</b>" in round_trip
    assert "<i>Italic</i>" in round_trip
    assert '<a href="https://example.com">link</a>' in round_trip


def test_html_payload_helpers():
    html = "<b>Bold</b>"
    text, parse_mode, entities = MessageMarkupConverter.html_payload(html)

    assert text == "Bold"
    assert parse_mode is None
    assert entities and entities[0].type == MessageEntity.BOLD

    html2 = "<i>Italic</i>"
    text2, parse_mode2, entities2 = MessageMarkupConverter.html_payload_with_parse_mode(html2)
    assert text2 == html2
    assert parse_mode2.upper() == "HTML"
    assert entities2 is None
