#  The MIT License (MIT)
#  Copyright (c) 2021-present foxwhite25
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.

from __future__ import annotations

from typing import (
    SupportsInt,
    TYPE_CHECKING,
    Union,
)

from .mixins import Hashable

if TYPE_CHECKING:
    SupportsIntCast = Union[SupportsInt, str, bytes, bytearray]

__all__ = (
    'Object',
)


class Object(Hashable):
    """代表一个通用的 QQ 对象。
    这个类的目的是允许你创建数据类的 ``微型`` 版，让你只传入一个 ID。
    大多数接受带有 ID 的特定数据类的函数也可以接受这个类作为替代。
    请注意，即使是这种情况，并非所有对象（如果有）实际上都继承自此类。
    在某些情况下，某些 websocket 事件以奇怪的顺序接收，当发生此类事件时，
    你将收到此类而不是实际的数据类。这些情况极为罕见。

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
