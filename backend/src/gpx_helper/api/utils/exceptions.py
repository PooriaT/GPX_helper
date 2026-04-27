from __future__ import annotations

from typing import TypeVar

from fastapi import HTTPException


T = TypeVar("T")


def as_bad_request(func, *args, **kwargs) -> T:
    """Execute a callable and map unexpected errors to HTTP 400 responses."""
    try:
        return func(*args, **kwargs)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
