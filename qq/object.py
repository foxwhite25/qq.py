from __future__ import annotations

from . import utils
from .mixins import Hashable

from typing import (
    SupportsInt,
    TYPE_CHECKING,
    Union,
)

if TYPE_CHECKING:
    SupportsIntCast = Union[SupportsInt, str, bytes, bytearray]

__all__ = (
    'Object',
)


class Object(Hashable):
    def __init__(self, id: SupportsIntCast):
        try:
            id = int(id)
        except ValueError:
            raise TypeError(f'id parameter must be convertable to int not {id.__class__!r}') from None
        else:
            self.id = id

    def __repr__(self) -> str:
        return f'<Object id={self.id!r}>'
