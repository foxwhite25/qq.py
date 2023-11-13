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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types.interaction import Interaction as InteractionPayload
    from .state import ConnectionState


class Interaction:
    """代表一个互动。

    请注意你需要在结束处理，或者判断权限结束后通过 :meth:`Interaction.success` 等函数回应互动，不然会导致超时。

    你也可以使用 async with 表达式在离开作用域时，如果未曾响应则自动调用 :meth:`Interaction.success` 回复成功。

    .. container:: operations

        .. describe:: x == y
            检查两个 guild 是否相等。
        .. describe:: x != y
            检查两个 guild 是否不相等。
        .. describe:: hash(x)
            返回 guild 的哈希值。
        .. describe:: str(x)
            返回 guild 的名称。

    Attributes
    ----------
    application_id: :class:`str`
        应用名称
    id: :class:`int`
        互动 ID
    chat_type: :class:`int`
        聊天类型？
    button_data: :class:`str`
        按钮名称/数据
    button_id: :class:`str`
        按钮 ID
    version: Optional[:class:`str`]
        互动版本
    """
    __slots__ = (
        "application_id",
        "chat_type",
        "button_data",
        "button_id",
        "user_id",
        "type",
        "version",
        "id",
        "_state",
        "_responded"
    )

    def __init__(self, state: ConnectionState, data: InteractionPayload):
        self._state = state
        self.application_id = data["application_id"]
        self.chat_type = data["chat_type"]
        if "data" in data and "resolved" in data["data"]:
            rs = data["data"]["resolved"]
            self.button_data = rs["button_data"]
            self.button_id = rs["button_id"]
            self.user_id = rs["user_id"]
        self.type = data["type"]
        self.version = data["version"]
        self.id = data["id"]
        self._responded = False

    async def __aenter__(self):
        return self

    async def __aexit__(self):
        if not self._responded:
            await self.success()

    async def _ack(self, code: int):
        if self._responded:
            return
        self._responded = True
        await self._state.http.ack_interaction(self.id, code)

    async def success(self):
        """|coro|
        回复操作成功。
        """

        await self._ack(0)

    async def failed(self):
        """|coro|
        回复操作失败。
        """

        await self._ack(1)

    async def too_frequent(self):
        """|coro|
        回复操作过于频繁。
        """

        await self._ack(2)

    async def duplicated(self):
        """|coro|
        回复操作为重复操作。
        """

        await self._ack(3)

    async def no_permission(self):
        """|coro|
        回复操作权限不足。
        """

        await self._ack(4)

    async def only_admin(self):
        """|coro|
        回复操作仅能被管理员调用。
        """

        await self._ack(5)
