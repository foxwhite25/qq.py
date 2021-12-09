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
    """代表一个通用的 QQ 对象。
    这个类的目的是允许您创建数据类的 ``微型`` 版，让你只传入一个 ID。
    大多数接受带有 ID 的特定数据类的函数也可以接受这个类作为替代。
    请注意，即使是这种情况，并非所有对象（如果有）实际上都继承自此类。
    在某些情况下，某些 websocket 事件以奇怪的顺序接收，当发生此类事件时，
    您将收到此类而不是实际的数据类。这些情况极为罕见。

    .. container:: operations

        .. describe:: x == y

            检查两个对象是否相等。

        .. describe:: x != y

            检查两个对象是否不相等。

        .. describe:: hash(x)

            返回对象的哈希值。

    Attributes
    -----------
    id: :class:`int`
        对象的 ID。
    """
    def __init__(self, id: SupportsIntCast):
        try:
            id = int(id)
        except ValueError:
            raise TypeError(f'id 参数必须可转换为 int 而不是 {id.__class__!r}') from None
        else:
            self.id = id

    def __repr__(self) -> str:
        return f'<Object id={self.id!r}>'
