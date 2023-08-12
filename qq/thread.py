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

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .channel import ThreadChannel
    from .state import ConnectionState
    from .types.forum import Thread as ThreadPayload, ThreadInfo

__all__ = (
    'Thread',
)


class Thread:
    """代表一个 QQ 帖子。

    Attributes
    -----------
    author: :class:`User`
        帖子的作者。
    guild: :class:`Guild`
        帖子所在的服务器。
    channel: :class:`ThreadChannel`
        帖子所在的频道。
    id: :class:`int`
        帖子 ID。
    title: :class:`str`
        帖子标题。
    content: :class:`str`
        帖子内容。
    created_at: :class:`datetime.datetime`
        发布时间。
    """

    __slots__ = (
        '_state',
        '_author',
        '_guild',
        '_channel',
        'author',
        'guild',
        'channel',
        'id',
        'title',
        'content',
        'created_at',
    )

    def __init__(
            self,
            *,
            state: ConnectionState,
            channel: ThreadChannel,
            data: ThreadPayload,
    ):
        self._state = state
        self._channel = int(data['channel_id'])
        self._author = int(data['author_id'])
        self._guild = int(data['guild_id'])
        self.channel = channel
        self.author = channel.guild.get_member(self._author)
        self.guild = self._state._get_guild(self._guild)
        self._update(data['thread_info'])

    def _update(self, data: ThreadInfo):
        self.id = int(data['thread_id'])
        self.title = data['title']
        self.content = data['content']
        self.created_at = datetime.fromtimestamp(data['datetime'])

    async def fetch(self):
        """从服务器获取最新的帖子数据。"""
        data = await self._state.http.get_thread(self.channel.id, self.id)
        self._update(data)

    async def delete(self):
        """删除帖子。"""
        await self._state.http.delete_thread(self.channel.id, self.id)
