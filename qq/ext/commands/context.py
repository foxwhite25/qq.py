from __future__ import annotations

import inspect
import re

from typing import Any, Dict, Generic, List, Optional, TYPE_CHECKING, TypeVar, Union

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

    from .bot import Bot, AutoShardedBot
    from .cog import Cog
    from .core import Command
    from .help import HelpCommand
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
        return await command(self, *args, **kwargs)

    async def reinvoke(self, *, call_hooks: bool = False, restart: bool = True) -> None:
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
        return self.prefix is not None and self.command is not None

    async def _get_channel(self) -> qq.abc.Messageable:
        return self.channel

    @property
    def clean_prefix(self) -> str:
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
        if self.command is None:
            return None
        return self.command.cog

    @qq.utils.cached_property
    def guild(self) -> Optional[Guild]:
        return self.message.guild

    @qq.utils.cached_property
    def channel(self) -> MessageableChannel:
        return self.message.channel

    @qq.utils.cached_property
    def author(self) -> Union[User, Member]:
        return self.message.author

    @qq.utils.cached_property
    def me(self) -> Union[Member, ClientUser]:
        # bot.user will never be None at this point.
        return self.guild.me if self.guild is not None else self.bot.user  # type: ignore

    async def send_help(self, *args: Any) -> Any:
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
            entity.qualified_name
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
