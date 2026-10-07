import re
from collections.abc import Sequence

from app.services.types import Detection


_PATTERN = re.compile(
    r"""
    (?<![A-Za-z0-9._%+\-@])

    (?P<local>
        [A-Za-z0-9_%+\-]+
        (?:\.[A-Za-z0-9_%+\-]+)*
    )

    @

    (?P<domain>
        (?:
            [A-Za-z0-9]
            (?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?
            \.
        )+
        [A-Za-z]{2,63}
    )

    (?![A-Za-z0-9_-]|\.[A-Za-z0-9_-])
    """,
    re.IGNORECASE | re.VERBOSE,
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


def _mask_email(keyword: str) -> str:
    local, domain = keyword.rsplit("@", 1)

    if len(local) <= 2:
        masked_local = local
    else:
        masked_local = (
            local[0]
            + ("*" * (len(local) - 2))
            + local[-1]
        )

    return f"{masked_local}@{domain}"


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

        replacement = _mask_email(keyword)

        text = (
            text[:start]
            + replacement
            + text[end:]
        )

    return text
