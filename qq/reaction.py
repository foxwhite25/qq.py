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

from typing import Any, TYPE_CHECKING, Union, Optional

__all__ = (
    'Reaction',
)

if TYPE_CHECKING:
    from .types.message import Reaction as ReactionPayload
    from .message import Message
    from .partial_emoji import PartialEmoji


class Reaction:
    """表示对消息的反应。

    根据创建此对象的方式，某些属性的值可以为 ``None`` 。

    .. container:: operations

        .. describe:: x == y

            检查两个反应是否相等。这通过检查表情符号是否相同来工作。因此，具有相同反应的两条消息将被视为 ``相同`` 。

        .. describe:: x != y

            检查两个反应是否不相等。

        .. describe:: hash(x)

            返回反应的哈希值。

        .. describe:: str(x)

            返回反应表情符号的字符串形式。

    Attributes
    -----------
    emoji: Union[:class:`PartialEmoji`, :class:`str`]
        反应表情。可能是自定义表情符号或 unicode 表情符号。
    count: :class:`int`
        该反应进行的次数
    message: :class:`Message`
        此反应的消息。
    """
    __slots__ = ('message', 'count', 'emoji', 'me')

    def __init__(self, *, message: Message, data: ReactionPayload,
                 emoji: Optional[Union[PartialEmoji, str]] = None):
        self.message: Message = message
        self.emoji: Union[PartialEmoji, str] = emoji or message._state.get_reaction_emoji(data['emoji'])
        self.count: int = data.get('count', 1)
        self.me: bool = data.get('me')

    # TODO: typeguard
    def is_custom_emoji(self) -> bool:
        """:class:`bool`: 这是自定义表情符号。"""
        return not isinstance(self.emoji, str)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and other.emoji == self.emoji

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return other.emoji != self.emoji
        return True

    def __hash__(self) -> int:
        return hash(self.emoji)

    def __str__(self) -> str:
        return str(self.emoji)

    def __repr__(self) -> str:
        return f'<Reaction emoji={self.emoji!r} me={self.me} count={self.count}>'
