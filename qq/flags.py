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

from typing import Type, Optional, Any, TypeVar, Callable, overload, Iterator, Tuple, ClassVar, Dict

__all__ = (
    'Intents',
)

FV = TypeVar('FV', bound='flag_value')
BF = TypeVar('BF', bound='BaseFlags')


class flag_value:
    def __init__(self, func: Callable[[Any], int]):
        self.flag = func(None)
        self.__doc__ = func.__doc__

    @overload
    def __get__(self: FV, instance: None, owner: Type[BF]) -> FV:
        ...

    @overload
    def __get__(self, instance: BF, owner: Type[BF]) -> bool:
        ...

    def __get__(self, instance: Optional[BF], owner: Type[BF]) -> Any:
        if instance is None:
            return self
        return instance._has_flag(self.flag)

    def __set__(self, instance: BF, value: bool) -> None:
        instance._set_flag(self.flag, value)

    def __repr__(self):
        return f'<flag_value flag={self.flag!r}>'


class alias_flag_value(flag_value):
    pass


def fill_with_flags(*, inverted: bool = False):
    def decorator(cls: Type[BF]):
        # fmt: off
        cls.VALID_FLAGS = {
            name: value.flag
            for name, value in cls.__dict__.items()
            if isinstance(value, flag_value)
        }
        # fmt: on

        if inverted:
            max_bits = max(cls.VALID_FLAGS.values()).bit_length()
            cls.DEFAULT_VALUE = -1 + (2 ** max_bits)
        else:
            cls.DEFAULT_VALUE = 0

        return cls

    return decorator


# n.b. flags must inherit from this and use the decorator above
class BaseFlags:
    VALID_FLAGS: ClassVar[Dict[str, int]]
    DEFAULT_VALUE: ClassVar[int]

    value: int

    __slots__ = ('value',)

    def __init__(self, **kwargs: bool):
        self.value = self.DEFAULT_VALUE
        for key, value in kwargs.items():
            if key not in self.VALID_FLAGS:
                raise TypeError(f'{key!r} is not a valid flag name.')
            setattr(self, key, value)

    @classmethod
    def _from_value(cls, value):
        self = cls.__new__(cls)
        self.value = value
        return self

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.value == other.value

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} value={self.value}>'

    def __iter__(self) -> Iterator[Tuple[str, bool]]:
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, alias_flag_value):
                continue

            if isinstance(value, flag_value):
                yield name, self._has_flag(value.flag)

    def _has_flag(self, o: int) -> bool:
        return (self.value & o) == o

    def _set_flag(self, o: int, toggle: bool) -> None:
        if toggle is True:
            self.value |= o
        elif toggle is False:
            self.value &= ~o
        else:
            raise TypeError(f'Value to set for {self.__class__.__name__} must be a bool.')


@fill_with_flags()
class Intents(BaseFlags):
    __slots__ = ()

    def __init__(self, **kwargs: bool):
        self.value = self.DEFAULT_VALUE
        for key, value in kwargs.items():
            if key not in self.VALID_FLAGS:
                raise TypeError(f'{key!r} is not a valid flag name.')
            setattr(self, key, value)

    @classmethod
    def all(cls: Type[Intents]) -> Intents:
        """一个工厂方法，它创建一个 :class:`Intents` 并启用所有内容。"""
        value = 0
        for bits in cls.VALID_FLAGS.values():
            value |= bits
        self = cls.__new__(cls)
        self.value = value
        return self

    @classmethod
    def none(cls: Type[Intents]) -> Intents:
        """一个工厂方法，它创建一个禁用一切的 :class:`Intents` 。"""
        self = cls.__new__(cls)
        self.value = self.DEFAULT_VALUE
        return self

    @classmethod
    def default(cls: Type[Intents]) -> Intents:
        """一个工厂方法，它创建一个 :class:`Intents`，
        除了 :attr:`guilds`, :attr:`members` 和 :attr:`at_guild_messages` 之外的所有内容都禁用。
        """
        self = cls.none()
        self.guilds = True
        self.members = True
        self.at_guild_messages = True
        return self

    @flag_value
    def guilds(self):
        """:class:`bool`: 频道相关事件是否开启。

        这对应于以下事件：

        - :func:`on_guild_join`
        - :func:`on_guild_update`
        - :func:`on_guild_remove`
        - :func:`on_guild_channel_update`
        - :func:`on_guild_channel_create`
        - :func:`on_guild_channel_delete`

        这也对应于缓存方面的以下属性和类：

        - :attr:`Client.guilds`
        - :class:`Guild` 以及它的所有属性。
        - :meth:`Client.get_channel`
        - :meth:`Client.get_all_channels`

        .. warning::

            强烈建议你启用此意图，以便你的机器人正常运行。
        """

        return 1 << 0

    @flag_value
    def members(self):
        """:class:`bool`: 频道成员相关事件是否开启。

        这对应于以下事件：

        - :func:`on_member_join`
        - :func:`on_member_remove`
        - :func:`on_member_update`

        这也对应于缓存方面的以下属性和类：

        - :meth:`Client.get_all_members`
        - :meth:`Client.get_user`
        - :meth:`Guild.chunk`
        - :meth:`Guild.fetch_members`
        - :meth:`Guild.get_member`
        - :attr:`Guild.members`
        - :attr:`Member.roles`
        - :attr:`Member.nick`
        - :attr:`User.name`
        - :attr:`User.avatar`
        """
        return 1 << 1

    @flag_value
    def guild_messages(self):
        """:class:`bool`: 频道消息相关事件是否开启。

        这对应于以下事件：

        - :func:`on_message` (只适用于频道)

        这也对应于缓存方面的以下属性和类：

        - :class:`Message`
        - :attr:`Client.cached_messages` (只适用于频道)

        .. note::

            现在来说，这个 Intents 需要额外的申请，如果没有适当的权限 Websocket 将无法连接。
        """
        return 1 << 9

    @flag_value
    def guild_reactions(self):
        """:class:`bool`: 频道消息反应相关事件是否开启。

        这对应于以下事件：

        - :func:`on_reaction_add` (只适用于频道)
        - :func:`on_reaction_remove` (只适用于频道)
        - :func:`on_raw_reaction_add` (只适用于频道)
        - :func:`on_raw_reaction_remove` (只适用于频道)

        这也对应于缓存方面的以下属性和类：

        - :attr:`Message.reactions` (只适用于频道信息)

        .. note::

            现在来说，这个 Intents 需要额外的申请，如果没有适当的权限 Websocket 将无法连接。
        """
        return 1 << 10

    @alias_flag_value
    def messages(self):
        """:class:`bool`: 是否启用频道和直接消息相关事件。
        这是设置或获取 :attr:`guild_messages` 和 :attr:`dm_messages` 的快捷方式。

        这对应于以下事件：
        - :func:`on_message` (both guilds and DMs)

        这也对应于缓存方面的以下属性和类：
        - :class:`Message`
        - :attr:`Client.cached_messages`

        .. note::

            现在来说，这个 Intents 需要额外的申请，如果没有适当的权限 Websocket 将无法连接。
        """

        return (1 << 12) | (1 << 9)

    @flag_value
    def dm_messages(self):
        """:class:`bool`: 是否启用直接消息相关事件。
        另见 :attr:`guild_messages` 来获取频道信息或 :attr:`messages` 同时获取两者。

        这对应于以下事件：

        - :func:`on_message` (only for DMs)

        这也对应于缓存方面的以下属性和类：

        - :class:`Message`
        - :attr:`Client.cached_messages` (only for DMs)

        .. note::

            现在来说，这个 Intents 需要额外的申请，如果没有适当的权限 Websocket 将无法连接。
        """
        return 1 << 12

    @flag_value
    def audit(self):
        """:class:`bool`: 消息审核相关事件是否开启。

        这对应于以下事件：

        - :func:`on_message_audit`
        """
        return 1 << 27

    @flag_value
    def thread(self):
        """:class:`bool`: 论坛相关事件是否开启。

        这对应于以下事件：

        - :func:`on_thread_create`
        - :func:`on_thread_update`
        - :func:`on_thread_delete`
        - :func:`on_post_create`
        - :func:`on_post_delete`
        - :func:`on_reply_create`
        - :func:`on_reply_delete`
        """
        return 1 << 28

    @flag_value
    def audio(self):
        """:class:`bool`: 频道提及机器人的消息相关事件是否开启。

        这对应于以下事件：

        - :func:`on_audio_start`
        - :func:`on_audio_stop`
        - :func:`on_mic_start`
        - :func:`on_mic_stop`
        """
        return 1 << 29

    @flag_value
    def at_guild_messages(self):
        """:class:`bool`: 频道提及机器人的消息相关事件是否开启。

        这对应于以下事件：

        - :func:`on_message` (只适用于频道)

        这也对应于缓存方面的以下属性和类：

        - :class:`Message`
        - :attr:`Client.cached_messages` (只适用于频道)
        """
        return 1 << 30
