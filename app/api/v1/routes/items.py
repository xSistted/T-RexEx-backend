"""Item endpoints — thin HTTP layer that delegates to ItemService."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.services.item_service import (
    ItemNotFoundError,
    ItemService,
    get_item_service,
)

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemRead], summary="List items")
def list_items(service: ItemService = Depends(get_item_service)) -> list[ItemRead]:
    return service.list_items()


@router.post(
    "",
    response_model=ItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
)
def create_item(
    payload: ItemCreate,
    service: ItemService = Depends(get_item_service),
) -> ItemRead:
    return service.create_item(payload)


@router.get("/{item_id}", response_model=ItemRead, summary="Get item by id")
def get_item(
    item_id: int,
    service: ItemService = Depends(get_item_service),
) -> ItemRead:
    try:
        return service.get_item(item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{item_id}", response_model=ItemRead, summary="Update item")
def update_item(
    item_id: int,
    payload: ItemUpdate,
    service: ItemService = Depends(get_item_service),
) -> ItemRead:
    try:
        return service.update_item(item_id, payload)
    except ItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete item",
)
def delete_item(
    item_id: int,
    service: ItemService = Depends(get_item_service),
) -> None:
    try:
        service.delete_item(item_id)
    except ItemNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
