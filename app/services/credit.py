import re
from collections.abc import Sequence

from app.services.types import Detection


_PATTERN = re.compile(
    r"(?<![0-9-])"
    r"(?:[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}|[0-9]{4} [0-9]{4} [0-9]{4} [0-9]{4}|[0-9]{16})"
    r"(?![0-9-])"
)


def detect(text: str) -> list[Detection]:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    return [
        {
            "position": (match.start(), match.end()),
            "keyword": match.group(0),
        }
        for match in _PATTERN.finditer(text)
    ]


def censor(
    text: str,
    detections: Sequence[Detection] | None = None,
) -> str:
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if detections is None:
        detections = detect(text)

    ordered = sorted(
        detections,
        key=lambda item: item["position"][0],
        reverse=True,
    )

    for detection in ordered:
        start, end = detection["position"]
        keyword = detection["keyword"]

        if not (
            isinstance(start, int)
            and isinstance(end, int)
            and 0 <= start < end <= len(text)
        ):
            raise ValueError(
                f"Invalid detection position: {(start, end)}"
            )

        if text[start:end] != keyword:
            raise ValueError(
                f"Detection does not match text at {(start, end)}"
            )

        replacement = re.sub(r"[0-9]", "X", keyword[:-4]) + keyword[-4:]

        text = (
            text[:start]
            + replacement
            + text[end:]
        )

    return text
