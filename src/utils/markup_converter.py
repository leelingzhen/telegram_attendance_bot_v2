from html.parser import HTMLParser
from typing import Dict, List, Optional, Sequence, Tuple

from telegram import MessageEntity


class _HtmlToEntityParser(HTMLParser):
    TAG_MAP = {
        "b": MessageEntity.BOLD,
        "strong": MessageEntity.BOLD,
        "i": MessageEntity.ITALIC,
        "em": MessageEntity.ITALIC,
        "u": MessageEntity.UNDERLINE,
        "s": MessageEntity.STRIKETHROUGH,
        "del": MessageEntity.STRIKETHROUGH,
        "code": MessageEntity.CODE,
        "pre": MessageEntity.PRE,
        "a": MessageEntity.TEXT_LINK,
    }

    def __init__(self):
        super().__init__()
        self._text_parts: List[str] = []
        self._open_tags: List[Dict] = []
        self.entities: List[MessageEntity] = []

    def handle_starttag(self, tag, attrs):
        entity_type = self.TAG_MAP.get(tag)
        if not entity_type:
            return
        attr_dict = dict(attrs)
        self._open_tags.append(
            {
                "tag": tag,
                "type": entity_type,
                "offset": self._current_offset,
                "attrs": attr_dict,
            }
        )

    def handle_endtag(self, tag):
        for idx in range(len(self._open_tags) - 1, -1, -1):
            entry = self._open_tags[idx]
            if entry["tag"] != tag:
                continue
            length = self._current_offset - entry["offset"]
            if length <= 0:
                self._open_tags.pop(idx)
                return
            kwargs = {
                "type": entry["type"],
                "offset": entry["offset"],
                "length": length,
            }
            if entry["type"] == MessageEntity.TEXT_LINK and "href" in entry["attrs"]:
                kwargs["url"] = entry["attrs"]["href"]
            if entry["type"] == MessageEntity.PRE and "language" in entry["attrs"]:
                kwargs["language"] = entry["attrs"]["language"]
            self.entities.append(MessageEntity(**kwargs))
            self._open_tags.pop(idx)
            return

    def handle_data(self, data):
        self._text_parts.append(data)

    @property
    def _current_offset(self) -> int:
        return len("".join(self._text_parts))

    def result(self) -> Tuple[str, List[MessageEntity]]:
        text = "".join(self._text_parts)
        return text, sorted(self.entities, key=lambda e: e.offset)


class MessageMarkupConverter:
    """Convert between HTML strings and Telegram entities."""

    @staticmethod
    def html_to_entities(html_text: str) -> Tuple[str, List[MessageEntity]]:
        parser = _HtmlToEntityParser()
        parser.feed(html_text)
        return parser.result()

    @staticmethod
    def entities_to_html(
        text: str, entities: Sequence[MessageEntity]
    ) -> str:
        start_tags: Dict[int, List[str]] = {}
        end_tags: Dict[int, List[str]] = {}

        def tag_pair(entity: MessageEntity) -> Tuple[str, str]:
            if entity.type == MessageEntity.BOLD:
                return "<b>", "</b>"
            if entity.type == MessageEntity.ITALIC:
                return "<i>", "</i>"
            if entity.type == MessageEntity.UNDERLINE:
                return "<u>", "</u>"
            if entity.type == MessageEntity.STRIKETHROUGH:
                return "<s>", "</s>"
            if entity.type == MessageEntity.CODE:
                return "<code>", "</code>"
            if entity.type == MessageEntity.PRE:
                return "<pre>", "</pre>"
            if entity.type == MessageEntity.TEXT_LINK:
                return f'<a href="{entity.url}">', "</a>"
            return "", ""

        for ent in sorted(entities, key=lambda e: e.offset):
            start, end = ent.offset, ent.offset + ent.length
            open_tag, close_tag = tag_pair(ent)
            if not open_tag:
                continue
            start_tags.setdefault(start, []).append(open_tag)
            end_tags.setdefault(end, []).append(close_tag)

        result_parts: List[str] = []
        for idx, char in enumerate(text):
            if idx in start_tags:
                result_parts.extend(start_tags[idx])
            result_parts.append(char)
            if idx + 1 in end_tags:
                result_parts.extend(end_tags[idx + 1])

        if len(text) in end_tags:
            result_parts.extend(end_tags[len(text)])

        return "".join(result_parts)

    @staticmethod
    def html_payload(html_text: str) -> Tuple[str, Optional[str], Optional[Sequence[MessageEntity]]]:
        """
        Convenience helper to prepare payload for send_message.
        Returns (text, parse_mode, entities)
        """
        text, entities = MessageMarkupConverter.html_to_entities(html_text)
        return text, None, entities

    @staticmethod
    def html_payload_with_parse_mode(html_text: str) -> Tuple[str, str, None]:
        """
        Prepare payload using Telegram's HTML parse mode instead of entities.
        Returns (text, parse_mode, entities)
        """
        return html_text, "HTML", None
