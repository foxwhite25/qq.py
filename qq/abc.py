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

import asyncio
from datetime import datetime
from typing import (
    overload, Optional, Union, List, TYPE_CHECKING, TypeVar, Dict, Any, runtime_checkable, Protocol, Tuple
)

from .enum import ChannelType
from .error import InvalidArgument
from .iterators import HistoryIterator
from .utils import MISSING

if TYPE_CHECKING:
    from .user import ClientUser
    from .embeds import Ark, Embed
    from .member import Member
    from .channel import CategoryChannel, TextChannel, PartialMessageable, DMChannel
    from .guild import Guild
    from .state import ConnectionState
    from .message import Message, MessageReference, PartialMessage
    from .types.channel import (
        Channel as ChannelPayload,
    )

    PartialMessageableChannel = Union[TextChannel, PartialMessageable, DMChannel]
    MessageableChannel = Union[PartialMessageableChannel]

__all__ = (
    'Messageable',
    'GuildChannel',
    'BaseAudioControl'
)


class _Undefined:
    def __repr__(self) -> str:
        return 'see-below'


_undefined: Any = _Undefined()


@runtime_checkable
class PrivateChannel(Protocol):
    """详细说明私人QQ频道上的常见操作的抽象类。

    以下实现了这个 ABC：

    - :class:`~qq.DMChannel`

    Attributes
    -----------
    me: :class:`~discord.ClientUser`
        代表你自己的用户。
    """

    __slots__ = ()

    me: ClientUser
    id: int


class Messageable:
    """一个 记录了可以发送消息的模型上的常见操作的ABC。

    以下实现了这个 ABC：

    - :class:`~qq.TextChannel`
    - :class:`~qq.User`
    - :class:`~qq.Member`
    - :class:`~qq.ext.commands.Context`

    """

    __slots__ = ()
    _state: ConnectionState

    async def _get_channel(self) -> Tuple[MessageableChannel, bool]:
        raise NotImplementedError

    @overload
    async def send(
            self,
            content: Optional[str] = ...,
            *,
            embed: Embed = ...,
            ark: Ark = ...,
            delete_after: float = ...,
            image: str = ...,
            msg_id: Union[Message, MessageReference, PartialMessage, str] = ...,
            reference: Union[Message, MessageReference, PartialMessage] = ...,
            mention_author: Member = ...,
    ) -> Union[Message, str]:
        ...

    async def send(
            self,
            content=None,
            *,
            image=None,
            msg_id='MESSAGE_CREATE',
            reference=None,
            mention_author=None,
            ark=None,
            embed=None,
            delete_after=None,
    ):
        """|coro|
        使用给定的内容向目的地发送消息。
        content 必须是可以通过 ``str(content)`` 转换为字符串的类型。
        如果不填入 ``reference`` 将会被腾讯视为主动消息。
        如果是主动信息，输出将会是 ``audit_id``。

        Parameters
        ------------
        content: Optional[:class:`str`]
            发送的信息内容。
        image: :class:`str`
            要发送的图片链接
        ark: Optional[:class:`qq.Ark`]
            要发送的 Ark 类
        embed: Optional[:class:`qq.Embed`]
            要发送的 Embed 类
        msg_id: Union[:class:`~qq.Message`, :class:`~qq.MessageReference`, :class:`~qq.PartialMessage`]
            被动消息使用的消息

            .. note::

                如果不使用 ``msg_id`` ，系统将判断为主动消息，主动消息默认每天往每个频道可推送的消息数是 20 条，超过会被限制。

            .. note::

                目前官方放宽了被动消息，无视即可。

        reference: Union[:class:`~qq.Message`, :class:`~qq.MessageReference`, :class:`~qq.PartialMessage`]
            对你正在回复的 :class:`~qq.Message` 的引用，可以使用 :meth:`~qq.Message.to_reference` 创建或直接作为 :class:`~qq.Message` 传递。
        mention_author: Optional[:class:`qq.Member`]
            如果设置了，将会在消息前面提及该用户。
        delete_after: Optional[:class:`float`]
            如果设置了，则等待该秒数之后自动撤回消息。如果删除失败，则它会被静默忽略。

        Raises
        --------
        ~qq.HTTPException
            发送信息失败。
        ~qq.Forbidden
            你没有发送消息的适当权限。
        ~qq.InvalidArgument
            ``reference`` 不是 :class:`~qq.Message` 、
            :class:`~qq.MessageReference` 或 :class:`~qq.PartialMessage` 。

        Returns
        ---------
        Union[:class:`~qq.Message`, :class:`~qq.MessageAudit`]
            发送的消息。
        """
        from .channel import TextChannel
        channel, direct = await self._get_channel()
        state = self._state
        content = str(content) if content is not None else None

        if mention_author is not None:
            content = mention_author.mention + content

        # if msg_id is not None:
        #     try:
        #         msg_id = msg_id.to_message_reference_dict()
        #     except AttributeError:
        #         raise InvalidArgument(
        #             'msg_id 参数必须是 Message、 MessageReference 或 PartialMessage') from None

        if reference is not None:
            try:
                reference = reference.to_message_reference_dict()
            except AttributeError:
                raise InvalidArgument(
                    'reference 参数必须是 Message、 MessageReference 或 PartialMessage') from None

        data = await state.http.send_message(
            channel.id,
            content,
            ark=ark,
            message_reference=reference,
            message_id=msg_id,
            image_url=image,
            embed=embed,
            direct=direct
        )

        # if msg_id is None:
        #     return data['data']['message_audit']['audit_id']

        ret = state.create_message(channel=channel, data=data, direct=direct)
        state.dispatch('message', ret)
        state._messages.append(ret)
        if channel and channel.__class__ in (TextChannel,):
            channel.last_message_id = ret.id
        if delete_after is not None:
            await ret.delete(delay=delete_after)  # type: ignore
        return ret

    async def fetch_message(self, id: str, /) -> Message:
        """|coro|
        从目的地检索单个 :class:`~qq.Message`。

        Parameters
        ------------
        id: :class:`str`
            要查找的消息 ID。

        Raises
        --------
        ~qq.NotFound
            未找到指定的消息。
        ~qq.Forbidden
            你没有获取消息所需的权限。
        ~qq.HTTPException
            检索消息失败。

        Returns
        --------
        :class:`~qq.Message`
            消息要求。
        """
        id = id
        channel, direct = await self._get_channel()
        data = await self._state.http.get_message(channel.id, id)
        return self._state.create_message(channel=channel, data=data['message'], direct=direct)

    def history(
            self,
            *,
            limit: Optional[int] = 100,
            before: Optional[datetime] = None,
            after: Optional[datetime] = None,
            around: Optional[datetime] = None,
            oldest_first: Optional[bool] = None,
    ) -> HistoryIterator:
        """返回允许接收目标消息历史记录的 :class:`~qq.AsyncIterator`。

        Examples
        ---------

        Usage ::

            counter = 0
            async for message in channel.history(limit=200):
                if message.author == client.user:
                    counter += 1

        Flattening into a list: ::
            messages = await channel.history(limit=123).flatten()
            # messages is now a list of Message...

        All parameters are optional.

        Parameters
        -----------
        limit: Optional[:class:`int`]
            要检索的消息数。如果为 ``None`` ，则检索频道中的每条消息。但是请注意，这会使其运行缓慢。
        before: Optional[:class:`datetime.datetime`]
            检索此日期或消息之前的消息。如果提供了日期时间，建议使用 UTC 感知日期时间。如果 datetime 是本地的，则假定它是本地时间。
        after: Optional[:class:`datetime.datetime`]
            在此日期或消息之后检索消息。如果提供了日期时间，建议使用 UTC 感知日期时间。如果 datetime 是本地的，则假定它是本地时间。
        around: Optional[:class:`datetime.datetime`]
            检索围绕此日期或消息的消息。如果提供了日期时间，建议使用 UTC 感知日期时间。如果 datetime 是本地的，则假定它是本地时间。
            使用此参数时，最大限制为 101。
            请注意，如果限制为偶数，则最多返回 limit + 1 条消息。
        oldest_first: Optional[:class:`bool`]
            如果设置为 ``True``，以最旧->最新的顺序返回消息。如果指定了 ``after`` ，则默认为 ``True`` ，否则为 ``False`` 。

        Raises
        ------
        ~qq.Forbidden
            你无权获取频道消息历史记录。
        ~qq.HTTPException
            获取消息历史记录的请求失败。

        Yields
        -------
        :class:`~qq.Message`
            已解析消息数据的消息。
        """
        return HistoryIterator(self, limit=limit, before=before, after=after, around=around, oldest_first=oldest_first)


GCH = TypeVar('GCH', bound='GuildChannel')


class GuildChannel:
    """详细介绍 QQ 子频道上常见操作的 ABC。

    以下实现了这个 ABC：

    - :class:`~qq.TextChannel`
    - :class:`~qq.VoiceChannel`
    - :class:`~qq.CategoryChannel`
    - :class:`~qq.ThreadChannel`
    - :class:`~qq.LiveChannel`
    - :class:`~qq.AppChannel`

    Attributes
    -----------
    name: :class:`str`
        子频道名称。
    guild: :class:`~qq.Guild`
        子频道所属的频道。
    position: :class:`int`
        在频道列表中的位置。这是一个从 0 开始的数字。例如顶部子是位置 0。
    """

    __slots__ = ()

    id: int
    name: str
    guild: Guild
    type: ChannelType
    position: int
    category_id: Optional[int]
    _state: ConnectionState

    if TYPE_CHECKING:
        def __init__(self, *, state: ConnectionState, guild: Guild, data: Dict[str, Any]):
            ...

    def __str__(self) -> str:
        return self.name

    @property
    def _sorting_bucket(self) -> int:
        raise NotImplementedError

    def _update(self, guild: Guild, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def _move(
            self,
            position: int,
            parent_id: Optional[Any] = None,
            *,
            reason: Optional[str],
    ) -> None:
        if position < 0:
            raise InvalidArgument('频道位置不能小于 0。')

        http = self._state.http
        bucket = self._sorting_bucket
        channels: List[GuildChannel] = [c for c in self.guild.channels if c._sorting_bucket == bucket]

        channels.sort(key=lambda c: c.position)

        try:
            # remove ourselves from the channel list
            channels.remove(self)
        except ValueError:
            # not there somehow lol
            return
        else:
            index = next((i for i, c in enumerate(channels) if c.position >= position), len(channels))
            # add ourselves at our designated position
            channels.insert(index, self)

        payload = []
        for index, c in enumerate(channels):
            d: Dict[str, Any] = {'id': c.id, 'position': index}
            if parent_id is not _undefined and c.id == self.id:
                d.update(parent_id=parent_id)
            payload.append(d)

        await asyncio.gather(*http.bulk_channel_update(self.guild.id, payload, reason=reason))

    async def _edit(self, options: Dict[str, Any], reason: Optional[str]) -> Optional[ChannelPayload]:
        try:
            parent = options.pop('category')
        except KeyError:
            parent_id = _undefined
        else:
            parent_id = parent and parent.id

        try:
            position = options.pop('position')
        except KeyError:
            if parent_id is not _undefined:
                options['parent_id'] = parent_id
        else:
            await self._move(position, parent_id=parent_id, reason=reason)

        try:
            ch_type = options['type']
        except KeyError:
            pass
        else:
            if not isinstance(ch_type, ChannelType):
                raise InvalidArgument('type 字段必须是 ChannelType 类型')
            options['type'] = ch_type.value

        if options:
            return await self._state.http.edit_channel(self.id, reason=reason, **options)

    @property
    def mention(self) -> str:
        """:class:`str`: 允许你提及频道的字符串。"""
        return f'<#{self.id}>'

    @property
    def category(self) -> Optional[CategoryChannel]:
        """Optional[:class:`~qq.CategoryChannel`]: 此频道所属的类别。如果没有类别，则为 ``None``。
        """
        return self.guild.get_channel(self.category_id)  # type: ignore

    async def delete(self, *, reason: Optional[str] = None) -> None:
        await self._state.http.delete_channel(self.id, reason=reason)

    async def _clone_impl(
            self: GCH,
            base_attrs: Dict[str, Any],
            *,
            name: Optional[str] = None,
            reason: Optional[str] = None,
    ) -> GCH:
        base_attrs['parent_id'] = self.category_id
        base_attrs['name'] = name or self.name
        guild_id = self.guild.id
        cls = self.__class__
        data = await self._state.http.create_channel(guild_id, self.type.value, reason=reason, **base_attrs)
        obj = cls(state=self._state, guild=self.guild, data=data)

        # temporarily add it to the cache
        self.guild._channels[obj.id] = obj  # type: ignore
        return obj

    async def clone(self: GCH, *, name: Optional[str] = None, reason: Optional[str] = None) -> GCH:
        raise NotImplementedError

    @overload
    async def move(
            self,
            *,
            beginning: bool,
            offset: int = MISSING,
            category: Optional[int] = MISSING,
            sync_permissions: bool = MISSING,
            reason: Optional[str] = MISSING,
    ) -> None:
        ...

    @overload
    async def move(
            self,
            *,
            end: bool,
            offset: int = MISSING,
            category: Optional[int] = MISSING,
            sync_permissions: bool = MISSING,
            reason: str = MISSING,
    ) -> None:
        ...

    @overload
    async def move(
            self,
            *,
            before: int,
            offset: int = MISSING,
            category: Optional[int] = MISSING,
            sync_permissions: bool = MISSING,
            reason: str = MISSING,
    ) -> None:
        ...

    @overload
    async def move(
            self,
            *,
            after: int,
            offset: int = MISSING,
            category: Optional[int] = MISSING,
            sync_permissions: bool = MISSING,
            reason: str = MISSING,
    ) -> None:
        ...

    async def move(self, **kwargs) -> None:
        """|coro|
        帮助你相对于其他频道移动频道。
        如果需要精确的位置移动，则应使用 ``edit`` 代替。

        Parameters
        ------------
        beginning: :class:`bool`
            是否将频道移动到频道列表（或类别，如果给定）的开头。这与 ``end`` 、 ``before`` 和 ``after`` 是互斥的。
        end: :class:`bool`
            是否将频道移动到频道列表（或类别，如果给定）的末尾。这与 ``beginning`` 、 ``before`` 和 ``after`` 是互斥的。
        before: :class:`GuildChannel`
            应该在我们当前频道之前的频道。这与 ``beginning`` 、 ``end`` 和` `after`` 是互斥的。
        after: :class:`GuildChannel`
            应该在我们当前频道之后的频道。这与 ``beginning`` 、 ``end`` 和 ``before`` 是互斥的。
        offset: :class:`int`
            偏移移动的通道数。
            例如，带有 ``beginning=True`` 的 ``2`` 偏移量会在开始后移动 2。
            正数将其移至下方，而负数将其移至上方。请注意，这个数字是相对的，并且是在 ``beginning`` 、 ``end`` 、 ``before`` 和 ``after`` 参数之后计算的。
        category: Optional[:class:`GuildChannel`]
            将此频道移动到的类别。如果给出 ``None``，则将其移出类别。如果移动类别频道，则忽略此参数。

        Raises
        -------
        InvalidArgument
            给出了无效的位置或传递了错误的参数组合。
        Forbidden
            你无权移动频道。
        HTTPException
            移动频道失败。
        """

        if not kwargs:
            return

        beginning, end = kwargs.get('beginning'), kwargs.get('end')
        before, after = kwargs.get('before'), kwargs.get('after')
        offset = kwargs.get('offset', 0)
        if sum(bool(a) for a in (beginning, end, before, after)) > 1:
            raise InvalidArgument('只能使用 [before, after, end, begin] 之一。')

        bucket = self._sorting_bucket
        parent_id = kwargs.get('category', MISSING)
        # fmt: off
        channels: List[GuildChannel]
        if parent_id not in (MISSING, None):
            parent_id = parent_id.id
            channels = [ch for ch in self.guild.channels
                        if ch._sorting_bucket == bucket and ch.category_id == parent_id]
        else:
            channels = [ch for ch in self.guild.channels
                        if ch._sorting_bucket == bucket and ch.category_id == self.category_id]
        # fmt: on

        channels.sort(key=lambda c: (c.position, c.id))

        try:
            # Try to remove ourselves from the channel list
            channels.remove(self)
        except ValueError:
            # If we're not there then it's probably due to not being in the category
            pass

        index = None
        if beginning:
            index = 0
        elif end:
            index = len(channels)
        elif before:
            index = next((i for i, c in enumerate(channels) if c.id == before.id), None)
        elif after:
            index = next((i + 1 for i, c in enumerate(channels) if c.id == after.id), None)

        if index is None:
            raise InvalidArgument('无法解析适当的移动位置')

        channels.insert(max((index + offset), 0), self)
        payload = []
        for index, channel in enumerate(channels):
            d = {'id': channel.id, 'position': index}
            if parent_id is not MISSING and channel.id == self.id:
                d.update(parent_id=parent_id)
            payload.append(d)

        await asyncio.gather(*self._state.http.bulk_channel_update(self.guild.id, payload))


class BaseAudioControl:
    __slots__ = (
        '_audio_url',
        '_text',
    )

    def __str__(self) -> str:
        return self._text

    def __repr__(self) -> str:
        attrs = [
            ('audio_url', self.audio_url),
            ('text', self._text),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'

    def set_url(self, url: str):
        """
        设定要开始的音频地址。

        Parameters
        ------------
        url: :class:`str`
            设定的音频地址
        """
        self._audio_url = url

    def set_text(self, text: str):
        """
        设定要开始的音频状态文本。

        Parameters
        ------------
        text: :class:`str`
            设定的音频状态文本
        """
        self._text = text

    @property
    def audio_url(self):
        return self._audio_url

    @property
    def text(self):
        return self._text
