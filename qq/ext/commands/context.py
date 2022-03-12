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

import inspect
import re
from typing import Any, Dict, Generic, List, Optional, TYPE_CHECKING, TypeVar, Union, Tuple

import qq.abc
import qq.utils
from qq.message import Message

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    from qq.abc import MessageableChannel
    from qq.guild import Guild
    from qq.member import Member
    from qq.state import ConnectionState
    from qq.user import ClientUser, User

    from .cog import Cog
    from .core import Command
    from .view import StringView

__all__ = (
    'Context',
)

MISSING: Any = qq.utils.MISSING

T = TypeVar('T')
BotT = TypeVar('BotT', bound="Union[Bot, AutoShardedBot]")
CogT = TypeVar('CogT', bound="Cog")

if TYPE_CHECKING:
    P = ParamSpec('P')
else:
    P = TypeVar('P')


class Context(qq.abc.Messageable, Generic[BotT]):
    r"""表示在其中调用命令的 context。

    该类包含大量元数据，可帮助你更多地了解调用的实际情况。
    这个类不是手动创建的，而是作为第一个参数传递给命令的。

    这个类实现了 :class:`~qq.abc.Messageable` ABC。

    Attributes
    -----------
    message: :class:`.Message`
        触发正在执行的命令的消息。
    bot: :class:`.Bot`
        包含正在执行的命令的机器人。
    args: :class:`list`
        传递给命令的转换参数列表。
        如果这是在 :func:`.on_command_error` 事件期间访问的，则此列表可能不完整。
    kwargs: :class:`dict`
        传递给命令的转换参数字典。
        类似于 :attr:`args`\ ，如果在 :func:`.on_command_error` 事件中访问了它，
        那么这个字典可能是不完整的。
    current_parameter: Optional[:class:`inspect.Parameter`]
        当前正在检查和转换的参数。这仅用于内部转换器。

    prefix: Optional[:class:`str`]
        用于调用命令的前缀。
    command: Optional[:class:`Command`]
        当前正在调用的命令。
    invoked_with: Optional[:class:`str`]
        触发此调用的命令名称。用于找出调用命令的别名。
    invoked_parents: List[:class:`str`]
        触发此调用的父级的命令名称。用于找出调用命令的别名。

        例如在命令 ``?a b c test`` 中，被调用的父对象是 ``['a', 'b', 'c']`` 。

    invoked_subcommand: Optional[:class:`Command`]
        被调用的子命令。
        如果没有调用有效的子命令，则这等于 ``None`` 。
    subcommand_passed: Optional[:class:`str`]
        试图调用子命令的字符串。这不必指向一个有效的注册子命令，而可以只指向一个无意义的字符串。
        如果没有传递任何内容来尝试调用子命令，则将其设置为 ``None`` 。
    command_failed: :class:`bool`
        指示命令是否未能解析、检查或调用的布尔值。
    """

    def __init__(self,
                 *,
                 message: Message,
                 bot: BotT,
                 view: StringView,
                 args: List[Any] = MISSING,
                 kwargs: Dict[str, Any] = MISSING,
                 prefix: Optional[str] = None,
                 command: Optional[Command] = None,
                 invoked_with: Optional[str] = None,
                 invoked_parents: List[str] = MISSING,
                 invoked_subcommand: Optional[Command] = None,
                 subcommand_passed: Optional[str] = None,
                 command_failed: bool = False,
                 current_parameter: Optional[inspect.Parameter] = None,
                 ):
        self.message: Message = message
        self.bot: BotT = bot
        self.args: List[Any] = args or []
        self.kwargs: Dict[str, Any] = kwargs or {}
        self.prefix: Optional[str] = prefix
        self.command: Optional[Command] = command
        self.view: StringView = view
        self.invoked_with: Optional[str] = invoked_with
        self.invoked_parents: List[str] = invoked_parents or []
        self.invoked_subcommand: Optional[Command] = invoked_subcommand
        self.subcommand_passed: Optional[str] = subcommand_passed
        self.command_failed: bool = command_failed
        self.current_parameter: Optional[inspect.Parameter] = current_parameter
        self._state: ConnectionState = self.message._state

    async def invoke(self, command: Command[CogT, P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
        r"""|coro|

        使用给定的参数调用命令。

        如果你只想调用 :class:`.Command` 在内部保存的回调，这很有用。

        .. note::

            这不会处理任何情况下的转换器、检查、冷却、调用前或调用后钩。
            它直接调用内部回调，就好像它是一个常规函数一样。

            使用此函数时，你必须注意传递正确的参数。

        Parameters
        -----------
        command: :class:`.Command`
            将要调用的命令。
        \*args
            要使用的参数。
        \*\*kwargs
            要使用的关键字参数。

        Raises
        -------
        TypeError
            缺少要调用的命令参数。
        """
        return await command(self, *args, **kwargs)

    async def reinvoke(self, *, call_hooks: bool = False, restart: bool = True) -> None:
        """|coro|

        再次调用命令。

        这类似于 :meth:`~.Context.invoke` ，但是它绕过检查、冷却和错误处理程序。

        .. note::

            如果你想绕过 :exc:`.UserInputError` 的异常，建议使用常规的 :meth:`~.Context.invoke` ，因为它会更自然地工作。
            毕竟，这最终会使用用户使用过的旧参数，因此只会再次失败。

        Parameters
        ------------
        call_hooks: :class:`bool`
            是否调用调用前或调用后钩。
        restart: :class:`bool`
            是从一开始还是从我们停止的地方开始调用链（即导致错误的命令）。默认是从我们停止的地方开始。

        Raises
        -------
        ValueError
            要重新调用的 context 无效。
        """
        cmd = self.command
        view = self.view
        if cmd is None:
            raise ValueError('This context is not valid.')

        # some state to revert to when we're done
        index, previous = view.index, view.previous
        invoked_with = self.invoked_with
        invoked_subcommand = self.invoked_subcommand
        invoked_parents = self.invoked_parents
        subcommand_passed = self.subcommand_passed

        if restart:
            to_call = cmd.root_parent or cmd
            view.index = len(self.prefix or '')
            view.previous = 0
            self.invoked_parents = []
            self.invoked_with = view.get_word()  # advance to get the root command
        else:
            to_call = cmd

        try:
            await to_call.reinvoke(self, call_hooks=call_hooks)
        finally:
            self.command = cmd
            view.index = index
            view.previous = previous
            self.invoked_with = invoked_with
            self.invoked_subcommand = invoked_subcommand
            self.invoked_parents = invoked_parents
            self.subcommand_passed = subcommand_passed

    @property
    def valid(self) -> bool:
        """:class:`bool`: 检查调用 context 是否有效以进行调用。"""
        return self.prefix is not None and self.command is not None

    async def _get_channel(self) -> Tuple[qq.abc.Messageable, bool]:
        return self.guild if self.message.direct else self.channel, self.message.direct

    @property
    def clean_prefix(self) -> str:
        """:class:`str`: 清理后的调用前缀。即提及是 ``@名字`` 而不是 ``<@id>`` 。
        """
        if self.prefix is None:
            return ''

        user = self.me
        # this breaks if the prefix mention is not the bot itself but I
        # consider this to be an *incredibly* strange use case. I'd rather go
        # for this common use case rather than waste performance for the
        # odd one.
        pattern = re.compile(r"<@!?%s>" % user.id)
        return pattern.sub("@%s" % user.display_name.replace('\\', r'\\'), self.prefix)

    @property
    def cog(self) -> Optional[Cog]:
        """Optional[:class:`.Cog`]: 返回与此 context 的命令关联的齿轮。如果不存在则 ``None`` 。"""

        if self.command is None:
            return None
        return self.command.cog

    @qq.utils.cached_property
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`.Guild`]: 返回与此 context 命令关联的频道。如果不可用则 ``None`` 。"""
        return self.message.guild

    @qq.utils.cached_property
    def channel(self) -> MessageableChannel:
        """Union[:class:`.abc.Messageable`]: 返回与此 context 命令关联的子频道。 :attr:`.Message.channel` 的简写。
        """
        return self.message.channel

    @qq.utils.cached_property
    def author(self) -> Union[User, Member]:
        """Union[:class:`~qq.User`, :class:`.Member`]:
        返回与此 context 命令关联的作者。 :attr:`.Message.author` 的简写
        """
        return self.message.author

    @qq.utils.cached_property
    def me(self) -> Union[Member, ClientUser]:
        """Union[:class:`.Member`, :class:`.ClientUser`]:
        类似于 :attr:`.Guild.me` ，但是它可以在私人消息 context 中返回 :class:`.ClientUser`。
        """
        # bot.user will never be None at this point.
        return self.guild.me if self.guild is not None else self.bot.user  # type: ignore

    async def send_help(self, *args: Any) -> Any:
        """send_help(entity=<bot>)

        |coro|

        如果给定，则显示指定实体的帮助命令。实体可以是命令或齿轮。

        如果没有给出实体，那么它将显示整个机器人的帮助。

        如果实体是一个字符串，那么它会查找它是 :class:`Cog` 还是一个 :class:`Command`。

        .. note::

            由于这个函数的工作方式，它不会返回类似于 :meth:`~.commands.HelpCommand.command_not_found` 的东西，
            而是在错误输入或没有帮助命令时返回 :class:`None`。

        Parameters
        ------------
        entity: Optional[Union[:class:`Command`, :class:`Cog`, :class:`str`]]
            要为其显示帮助的实体。

        Returns
        --------
        Any
            帮助命令的结果，如果有的话。
        """
        from .core import Group, Command, wrap_callback
        from .errors import CommandError

        bot = self.bot
        cmd = bot.help_command

        if cmd is None:
            return None

        cmd = cmd.copy()
        cmd.context = self
        if len(args) == 0:
            await cmd.prepare_help_command(self, None)
            mapping = cmd.get_bot_mapping()
            injected = wrap_callback(cmd.send_bot_help)
            try:
                return await injected(mapping)
            except CommandError as e:
                await cmd.on_help_command_error(self, e)
                return None

        entity = args[0]
        if isinstance(entity, str):
            entity = bot.get_cog(entity) or bot.get_command(entity)

        if entity is None:
            return None

        try:
            _ = entity.qualified_name
        except AttributeError:
            # if we're here then it's not a cog, group, or command.
            return None

        await cmd.prepare_help_command(self, entity.qualified_name)

        try:
            if hasattr(entity, '__cog_commands__'):
                injected = wrap_callback(cmd.send_cog_help)
                return await injected(entity)
            elif isinstance(entity, Group):
                injected = wrap_callback(cmd.send_group_help)
                return await injected(entity)
            elif isinstance(entity, Command):
                injected = wrap_callback(cmd.send_command_help)
                return await injected(entity)
            else:
                return None
        except CommandError as e:
            await cmd.on_help_command_error(self, e)

    @qq.utils.copy_doc(Message.reply)
    async def reply(self, content: Optional[str] = None, **kwargs: Any) -> Message:
        return await self.message.reply(content, **kwargs)
