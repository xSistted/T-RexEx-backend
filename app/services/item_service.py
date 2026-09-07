"""Business logic for items.

This layer knows nothing about HTTP — it deals in plain data and domain rules.
Swap the in-memory store for a real database/repository later without touching routes.
"""

from app.schemas.item import ItemCreate, ItemRead, ItemUpdate


class ItemNotFoundError(Exception):
    """Raised when an item does not exist."""

    def __init__(self, item_id: int) -> None:
        self.item_id = item_id
        super().__init__(f"Item {item_id} not found")


class ItemService:
    """In-memory item store. Replace internals with a DB repository when needed."""

    def __init__(self) -> None:
        self._items: dict[int, ItemRead] = {}
        self._next_id: int = 1

    def list_items(self) -> list[ItemRead]:
        return list(self._items.values())

    def get_item(self, item_id: int) -> ItemRead:
        item = self._items.get(item_id)
        if item is None:
            raise ItemNotFoundError(item_id)
        return item

    def create_item(self, payload: ItemCreate) -> ItemRead:
        item = ItemRead(id=self._next_id, **payload.model_dump())
        self._items[item.id] = item
        self._next_id += 1
        return item

    def update_item(self, item_id: int, payload: ItemUpdate) -> ItemRead:
        existing = self.get_item(item_id)
        updated = existing.model_copy(update=payload.model_dump(exclude_unset=True))
        self._items[item_id] = updated
        return updated

    def delete_item(self, item_id: int) -> None:
        if item_id not in self._items:
            raise ItemNotFoundError(item_id)
        del self._items[item_id]


# Single shared instance used as a FastAPI dependency.
_item_service = ItemService()


def get_item_service() -> ItemService:
    """Dependency provider — override in tests via app.dependency_overrides."""
    return _item_service
