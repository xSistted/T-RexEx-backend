from typing import TypedDict


class Detection(TypedDict):
    position: tuple[int, int]
    keyword: str