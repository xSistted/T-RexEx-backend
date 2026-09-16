"""Business logic for masking sensitive customer data.

Every masking function accepts a string and returns a string.
New masking features can be added to MASKERS without changing the API route.
"""

import re
from collections.abc import Callable


# =============================================================================
# Credit Card
# =============================================================================

_CARD_PATTERN = re.compile(
    r"(?<![0-9-])"
    r"[0-9]{4}-[0-9]{4}-[0-9]{4}-"
    r"(?P<last4>[0-9]{4})"
    r"(?![0-9-])"
)


def mask_card(text: str) -> str:
    """
    Mask credit card numbers while preserving the final 4 digits.

    Example:
        1234-5678-9012-3456
        -> XXXX-XXXX-XXXX-3456
    """

    return _CARD_PATTERN.sub(
        r"XXXX-XXXX-XXXX-\g<last4>",
        text,
    )


# =============================================================================
# Email
# =============================================================================

_EMAIL_PATTERN = re.compile(
    r"""
    (?<![A-Za-z0-9._%+\-])

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

    (?![A-Za-z0-9._-])
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _replace_email(match: re.Match[str]) -> str:
    local = match.group("local")
    domain = match.group("domain")

    # Avoid processing suspiciously oversized addresses.
    if len(local) > 64 or len(domain) > 253:
        return match.group(0)

    # With 1-2 characters there is nothing between
    # the first and last character to hide.
    if len(local) <= 2:
        masked_local = local
    else:
        masked_local = (
            local[0]
            + ("*" * (len(local) - 2))
            + local[-1]
        )

    return f"{masked_local}@{domain}"


def mask_email(text: str) -> str:
    """
    Mask email username except its first and last characters.

    Example:
        somchai.d@company.com
        -> s*******d@company.com
    """

    return _EMAIL_PATTERN.sub(
        _replace_email,
        text,
    )


# =============================================================================
# Masking Pipeline
# =============================================================================

Masker = Callable[[str], str]


# Register every masking function here.
#
# Future teammates only need to add their function to this tuple.
MASKERS: tuple[Masker, ...] = (
    mask_card,
    mask_email,
)


def mask_text(text: str) -> str:
    """
    Run all registered masking functions over the input text.

    Every registered function must follow:

        mask_something(text: str) -> str
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    for masker in MASKERS:
        text = masker(text)

    return text