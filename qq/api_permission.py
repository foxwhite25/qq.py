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

from .channel import TextChannel

if TYPE_CHECKING:
    from typing import Coroutine
    from .state import ConnectionState
    from .guild import Guild
    from .types.permission import (
        Permission as PermissionPayload,
    )

__all__ = ('Permission',)


class Permission:
    """
    代表机器人 API 接口权限

    Attributes
    ----------
    path: :class:`str`
        API 接口名，例如 ``/guilds/{guild_id}/members/{user_id}``
    method: :class:`str`
        请求方法，例如 ``GET``
    desc: :class:`str`
        API 接口名称，例如 ``获取频道信``
    """
    __slots__ = (
        'path',
        'method',
        'desc',
        '_auth_status',
        '_state',
        '_guild'
    )

    def __init__(self, data: PermissionPayload, state: ConnectionState, guild: Guild):
        self.path = data.get('path')
        self.method = data.get('method')
        self.desc = data.get('desc')
        self._auth_status = data.get('auth_status')
        self._state = state
        self._guild = guild

    def __repr__(self):
        return f"<Permission desc={self.desc} path={self.method} {self.path}>"

    @property
    def enabled(self):
        """:class:`bool`: 是否已经启用。"""
        return True if self._auth_status == 1 else False

    @property
    def disabled(self):
        """:class:`bool`: 是否已经禁用。"""
        return True if self._auth_status != 1 else False

    def demand(self, channel: TextChannel, desc=None) -> Coroutine:
        return self._state.http.demand_permission(
            guild_id=self._guild.id,
            channel_id=channel.id,
            desc=desc or self.desc,
            path=self.path,
            method=self.method
        )
