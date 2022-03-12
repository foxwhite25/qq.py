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
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    Literal,
    Optional,
    TYPE_CHECKING,
    List,
    Protocol,
    Type,
    TypeVar,
    Tuple,
    Union,
    runtime_checkable,
)

import qq
from .errors import *

if TYPE_CHECKING:
    from .context import Context
    from qq.message import PartialMessageableChannel

__all__ = (
    'Converter',
    'ObjectConverter',
    'MemberConverter',
    'UserConverter',
    'MessageConverter',
    'PartialMessageConverter',
    'TextChannelConverter',
    'GuildConverter',
    'RoleConverter',
    'ColourConverter',
    'ColorConverter',
    'VoiceChannelConverter',
    'CategoryChannelConverter',
    'ThreadChannelConverter',
    'LiveChannelConverter',
    'AppChannelConverter',
    'IDConverter',
    'GuildChannelConverter',
    'clean_content',
    'Greedy',
    'run_converters',
)


def _get_from_guilds(bot, getter, argument):
    result = None
    for guild in bot.guilds:
        result = getattr(guild, getter)(argument)
        if result:
            return result
    return result


_utils_get = qq.utils.get
T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
CT = TypeVar('CT', bound=qq.abc.GuildChannel)


@runtime_checkable
class Converter(Protocol[T_co]):
    """需要传递 :class:`.Context` 的自定义转换器的基类才有用。

    这允许你实现功能类似于特殊情况的 ``qq`` 类的转换器。

    派生自此的类应覆盖 :meth:`~.Converter.convert` 方法以执行其转换逻辑。这个方法必须是一个 :ref:`协程 <coroutine>`。
    """

    async def convert(self, ctx: Context, argument: str) -> T_co:
        """|coro|

        要覆盖以执行转换逻辑的方法。

        如果在转换时发现错误，建议引发 :exc:`.CommandError` 派生异常，因为它会正确传播到错误处理程序。

        Parameters
        -----------
        ctx: :class:`.Context`
            正在使用参数的调用 context 。
        argument: :class:`str`
            正在转换的参数。

        Raises
        -------
        :exc:`.CommandError`
            转换参数时发生一般异常。
        :exc:`.BadArgument`
            转换器无法转换参数。
        """
        raise NotImplementedError('派生类需要实现它。')


_ID_REGEX = re.compile(r'([0-9]{15,20})$')


class IDConverter(Converter[T_co]):
    @staticmethod
    def _get_id_match(argument):
        return _ID_REGEX.match(argument)


class ObjectConverter(IDConverter[qq.Object]):
    """转换为 :class:`~qq.Object`。

    参数必须遵循有效的 ID 或提及格式（例如`<@80088516616269824>`）。

    查找策略如下（按顺序）：

    1. 通过ID查找。
    2. 按成员、身份组或频道提及查找。
    """

    async def convert(self, ctx: Context, argument: str) -> qq.Object:
        match = self._get_id_match(argument) or re.match(r'<(?:@(?:!|&)?|#)([0-9]{15,20})>$', argument)

        if match is None:
            raise ObjectNotFound(argument)

        result = int(match.group(1))

        return qq.Object(id=result)


class MemberConverter(IDConverter[qq.Member]):
    """转换为 :class:`~qq.Member`。

    所有查找都是通过本地频道进行的。如果在 DM  context 中，则查找由全局缓存完成。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 按提及查找。
    4. 按名称查找。
    5. 按昵称查找。

    """

    async def query_member_named(self, guild, argument):
        cache = guild._state.member_cache_flags.joined
        if len(argument) > 5 and argument[-5] == '#':
            username, _, discriminator = argument.rpartition('#')
            members = await guild.query_members(username, limit=100, cache=cache)
            return qq.utils.get(members, name=username, discriminator=discriminator)
        else:
            members = await guild.query_members(argument, limit=100, cache=cache)
            return qq.utils.find(lambda m: m.name == argument or m.nick == argument, members)

    async def query_member_by_id(self, bot, guild, user_id):
        ws = bot._get_websocket(shard_id=guild.shard_id)
        cache = guild._state.member_cache_flags.joined
        try:
            member = await guild.fetch_member(user_id)
        except qq.HTTPException:
            return None

        if cache:
            guild._add_member(member)
        return member

    async def convert(self, ctx: Context, argument: str) -> qq.Member:
        bot = ctx.bot
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]{15,20})>$', argument)
        guild = ctx.guild
        result = None
        user_id = None
        if match is None:
            # not a mention...
            if guild:
                result = guild.get_member_named(argument)
            else:
                result = _get_from_guilds(bot, 'get_member_named', argument)
        else:
            user_id = int(match.group(1))
            if guild:
                result = guild.get_member(user_id) or await guild.fetch_member(user_id) or _utils_get(
                    ctx.message.mentions, id=user_id)
            else:
                result = _get_from_guilds(bot, 'get_member', user_id)

        if result is None:
            if guild is None:
                raise MemberNotFound(argument)

            if user_id is not None:
                result = await self.query_member_by_id(bot, guild, user_id)
            else:
                result = await self.query_member_named(guild, argument)

            if not result:
                raise MemberNotFound(argument)

        return result


class UserConverter(IDConverter[qq.User]):
    """转换为 :class:`~qq.User`。

    所有查找都是通过全局用户缓存进行的。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 通过提及查找。
    3. 按名称查找。
    """

    async def convert(self, ctx: Context, argument: str) -> qq.User:
        match = self._get_id_match(argument) or re.match(r'<@!?([0-9]{15,20})>$', argument)
        result = None
        state = ctx._state

        if match is not None:
            user_id = int(match.group(1))
            result = ctx.bot.get_user(user_id) or _utils_get(ctx.message.mentions, id=user_id)
            if result is None:
                try:
                    result = await ctx.bot.fetch_user(user_id)
                except qq.HTTPException:
                    raise UserNotFound(argument) from None

            return result

        arg = argument

        # Remove the '@' character if this is the first character from the argument
        if arg[0] == '@':
            # Remove first character
            arg = arg[1:]

        # check for discriminator if it exists,
        if len(arg) > 5 and arg[-5] == '#':
            discrim = arg[-4:]
            name = arg[:-5]
            predicate = lambda u: u.name == name and u.discriminator == discrim
            result = qq.utils.find(predicate, state._users.values())
            if result is not None:
                return result

        predicate = lambda u: u.name == arg
        result = qq.utils.find(predicate, state._users.values())

        if result is None:
            raise UserNotFound(argument)

        return result


class PartialMessageConverter(Converter[qq.PartialMessage]):
    """转换为 :class:`qq.PartialMessage`。

    创建策略如下（按顺序）：

    1. 通过  ``{channel ID}-{message ID}``
    2. 通过消息 ID
    """

    @staticmethod
    def _get_id_matches(ctx, argument):
        id_regex = re.compile(r'(?:(?P<channel_id>[0-9]{15,20})-)?(?P<message_id>[0-9]{15,20})$')
        link_regex = re.compile(
            r'https?://(?:(ptb|canary|www)\.)?qq(?:app)?\.com/channels/'
            r'(?P<guild_id>[0-9]{15,20}|@me)'
            r'/(?P<channel_id>[0-9]{15,20})/(?P<message_id>[0-9]{15,20})/?$'
        )
        match = id_regex.match(argument) or link_regex.match(argument)
        if not match:
            raise MessageNotFound(argument)
        data = match.groupdict()
        channel_id = int(data.get('channel_id'))
        message_id = int(data['message_id'])
        guild_id = data.get('guild_id')
        if guild_id is None:
            guild_id = ctx.guild and ctx.guild.id
        elif guild_id == '@me':
            guild_id = None
        else:
            guild_id = int(guild_id)
        if channel_id is None:
            channel_id = ctx.channel.id
        return guild_id, message_id, channel_id

    @staticmethod
    def _resolve_channel(ctx, guild_id, channel_id) -> Optional[PartialMessageableChannel]:
        if guild_id is not None:
            guild = ctx.bot.get_guild(guild_id)
            if guild is not None and channel_id is not None:
                return guild._resolve_channel(channel_id)  # type: ignore
            else:
                return None
        else:
            return ctx.bot.get_channel(channel_id) if channel_id else ctx.channel

    async def convert(self, ctx: Context, argument: str) -> qq.PartialMessage:
        guild_id, message_id, channel_id = self._get_id_matches(ctx, argument)
        channel = self._resolve_channel(ctx, guild_id, channel_id)
        if not channel:
            raise ChannelNotFound(channel_id)
        return qq.PartialMessage(channel=channel, id=message_id)


class MessageConverter(IDConverter[qq.Message]):
    """转换为 :class:`qq.Message`。

    查找策略如下（按顺序）：

    1. 按 ``{channel ID}-{message ID}`` 查找
    2. 按消息 ID 查找
    """

    async def convert(self, ctx: Context, argument: str) -> qq.Message:
        guild_id, message_id, channel_id = PartialMessageConverter._get_id_matches(ctx, argument)
        message = ctx.bot._connection._get_message(message_id)
        if message:
            return message
        channel = PartialMessageConverter._resolve_channel(ctx, guild_id, channel_id)
        if not channel:
            raise ChannelNotFound(channel_id)
        try:
            return await channel.fetch_message(message_id)
        except qq.NotFound:
            raise MessageNotFound(argument)
        except qq.Forbidden:
            raise ChannelNotReadable(channel)


class GuildChannelConverter(IDConverter[qq.abc.GuildChannel]):
    """转换为 :class:`~qq.abc.GuildChannel`。

    所有查找都是通过本地频道进行的。如果在 DM  context 中，则查找由全局缓存完成。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 通过提及查找。
    3. 按名称查找。
    """

    async def convert(self, ctx: Context, argument: str) -> qq.abc.GuildChannel:
        return self._resolve_channel(ctx, argument, 'channels', qq.abc.GuildChannel)

    @staticmethod
    def _resolve_channel(ctx: Context, argument: str, attribute: str, type: Type[CT]) -> CT:
        bot = ctx.bot

        match = IDConverter._get_id_match(argument) or re.match(r'<#([0-9]{15,20})>$', argument)
        result = None
        guild = ctx.guild

        if match is None:
            # not a mention
            if guild:
                iterable: Iterable[CT] = getattr(guild, attribute)
                result: Optional[CT] = qq.utils.get(iterable, name=argument)
            else:

                def check(c):
                    return isinstance(c, type) and c.name == argument

                result = qq.utils.find(check, bot.get_all_channels())
        else:
            channel_id = int(match.group(1))
            if guild:
                result = guild.get_channel(channel_id)
            else:
                result = _get_from_guilds(bot, 'get_channel', channel_id)

        if not isinstance(result, type):
            raise ChannelNotFound(argument)

        return result


class TextChannelConverter(IDConverter[qq.TextChannel]):
    """转换为 :class:`~qq.TextChannel`。

    所有查找都是通过本地频道进行的。如果在 DM  context 中，则查找由全局缓存完成。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 通过提及查找。
    3. 按名称查找
    """

    async def convert(self, ctx: Context, argument: str) -> qq.TextChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'text_channels', qq.TextChannel)


class VoiceChannelConverter(IDConverter[qq.VoiceChannel]):
    """转换为 :class:`~qq.VoiceChannel`。

    所有查找都是通过本地频道进行的。如果在 DM  context 中，则查找由全局缓存完成。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 通过提及查找。
    3. 按名称查找
    """

    async def convert(self, ctx: Context, argument: str) -> qq.VoiceChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'voice_channels', qq.VoiceChannel)


class CategoryChannelConverter(IDConverter[qq.CategoryChannel]):
    """转换为 :class:`~qq.CategoryChannel`。

    所有查找都是通过本地频道进行的。如果在 DM  context 中，则查找由全局缓存完成。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 通过提及查找。
    3. 按名称查找
    """

    async def convert(self, ctx: Context, argument: str) -> qq.CategoryChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'categories', qq.CategoryChannel)


class AppChannelConverter(IDConverter[qq.AppChannel]):
    """转换为 :class:`~qq.AppChannel`。

    所有查找都是通过本地频道进行的。如果在 DM  context 中，则查找由全局缓存完成。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 通过提及查找。
    3. 按名称查找
    """

    async def convert(self, ctx: Context, argument: str) -> qq.CategoryChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'app_channels', qq.CategoryChannel)


class LiveChannelConverter(IDConverter[qq.LiveChannel]):
    """转换为 :class:`~qq.LiveChannel`。

    所有查找都是通过本地频道进行的。如果在 DM  context 中，则查找由全局缓存完成。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 通过提及查找。
    3. 按名称查找
    """

    async def convert(self, ctx: Context, argument: str) -> qq.CategoryChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'live_channels', qq.CategoryChannel)


class ThreadChannelConverter(IDConverter[qq.ThreadChannel]):
    """转换为 :class:`~qq.ThreadChannel`。

    所有查找都是通过本地频道进行的。如果在 DM  context 中，则查找由全局缓存完成。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 通过提及查找。
    3. 按名称查找
    """

    async def convert(self, ctx: Context, argument: str) -> qq.CategoryChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'thread_channels', qq.CategoryChannel)


class ColourConverter(Converter[qq.Colour]):
    """转换为 :class:`~qq.Colour`。

    接受以下格式：

    - ``0x<hex>``
    - ``#<hex>``
    - ``0x#<hex>``
    - ``rgb(<number>, <number>, <number>)``
    - :class:`~qq.Colour` 中的任何 ``classmethod``

        - 名称中的``_`` 可以选择替换为空格。

    像 CSS 一样，``<number>`` 可以是 0-255 或 0-100%，而 ``<hex>`` 可以是 6 位十六进制数字或 3 位十六进制快捷方式（例如 fff）。
    """

    RGB_REGEX = re.compile(r'rgb\s*\((?P<r>[0-9]{1,3}%?)\s*,\s*(?P<g>[0-9]{1,3}%?)\s*,\s*(?P<b>[0-9]{1,3}%?)\s*\)')

    def parse_hex_number(self, argument):
        arg = ''.join(i * 2 for i in argument) if len(argument) == 3 else argument
        try:
            value = int(arg, base=16)
            if not (0 <= value <= 0xFFFFFF):
                raise BadColourArgument(argument)
        except ValueError:
            raise BadColourArgument(argument)
        else:
            return qq.Color(value=value)

    def parse_rgb_number(self, argument, number):
        if number[-1] == '%':
            value = int(number[:-1])
            if not (0 <= value <= 100):
                raise BadColourArgument(argument)
            return round(255 * (value / 100))

        value = int(number)
        if not (0 <= value <= 255):
            raise BadColourArgument(argument)
        return value

    def parse_rgb(self, argument, *, regex=RGB_REGEX):
        match = regex.match(argument)
        if match is None:
            raise BadColourArgument(argument)

        red = self.parse_rgb_number(argument, match.group('r'))
        green = self.parse_rgb_number(argument, match.group('g'))
        blue = self.parse_rgb_number(argument, match.group('b'))
        return qq.Color.from_rgb(red, green, blue)

    async def convert(self, ctx: Context, argument: str) -> qq.Colour:
        if argument[0] == '#':
            return self.parse_hex_number(argument[1:])

        if argument[0:2] == '0x':
            rest = argument[2:]
            # Legacy backwards compatible syntax
            if rest.startswith('#'):
                return self.parse_hex_number(rest[1:])
            return self.parse_hex_number(rest)

        arg = argument.lower()
        if arg[0:3] == 'rgb':
            return self.parse_rgb(arg)

        arg = arg.replace(' ', '_')
        method = getattr(qq.Colour, arg, None)
        if arg.startswith('from_') or method is None or not inspect.ismethod(method):
            raise BadColourArgument(arg)
        return method()


ColorConverter = ColourConverter


class RoleConverter(IDConverter[qq.Role]):
    """转换为 :class:`~qq.Role`。

    所有查找都是通过本地频道进行的。如果在 DM  context 中，转换器会引发 :exc:`.NoPrivateMessage` 异常。

    查找策略如下（按顺序）：

    1. 通过 ID 查找。
    2. 通过提及查找。
    3. 按名称查找
    """

    async def convert(self, ctx: Context, argument: str) -> qq.Role:
        guild = ctx.guild
        if not guild:
            raise NoPrivateMessage()

        match = self._get_id_match(argument) or re.match(r'<@&([0-9]{15,20})>$', argument)
        if match:
            result = guild.get_role(int(match.group(1)))
        else:
            result = qq.utils.get(guild._roles.values(), name=argument)

        if result is None:
            raise RoleNotFound(argument)
        return result


class GuildConverter(IDConverter[qq.Guild]):
    """转换为 :class:`~qq.Guild`。

    查找策略如下（按顺序）：

    1. 通过 ID 查找.
    2. 按名称查找。 （对于具有多个匹配名称的频道，没有消歧义）。
    """

    async def convert(self, ctx: Context, argument: str) -> qq.Guild:
        match = self._get_id_match(argument)
        result = None

        if match is not None:
            guild_id = int(match.group(1))
            result = ctx.bot.get_guild(guild_id)

        if result is None:
            result = qq.utils.get(ctx.bot.guilds, name=argument)

            if result is None:
                raise GuildNotFound(argument)
        return result


class clean_content(Converter[str]):
    """将参数转换为提及所述内容的清理版本。

    这与 :attr:`~qq.Message.clean_content` 的行为类似。

    Attributes
    ------------
    fix_channel_mentions: :class:`bool`
        是否清理频道提及。
    use_nicknames: :class:`bool`
        转换提及时是否使用昵称。
    escape_markdown: :class:`bool`
        是否也转义特殊的 Markdown 字符。
    remove_markdown: :class:`bool`
        是否也删除特殊的 Markdown 字符。 ``escape_markdown`` 不支持此选项

        .. versionadded:: 1.7
    """

    def __init__(
            self,
            *,
            fix_channel_mentions: bool = False,
            use_nicknames: bool = True,
            escape_markdown: bool = False,
            remove_markdown: bool = False,
    ) -> None:
        self.fix_channel_mentions = fix_channel_mentions
        self.use_nicknames = use_nicknames
        self.escape_markdown = escape_markdown
        self.remove_markdown = remove_markdown

    async def convert(self, ctx: Context, argument: str) -> str:
        msg = ctx.message

        if ctx.guild:

            def resolve_member(id: int) -> str:
                m = _utils_get(msg.mentions, id=id) or ctx.guild.get_member(id)
                return f'@{m.display_name if self.use_nicknames else m.name}' if m else '@已删除用户'

            def resolve_role(id: int) -> str:
                r = _utils_get(msg.role_mentions, id=id) or ctx.guild.get_role(id)
                return f'@{r.name}' if r else '@已删除身份组'

        else:

            def resolve_member(id: int) -> str:
                m = _utils_get(msg.mentions, id=id) or ctx.bot.get_user(id)
                return f'@{m.name}' if m else '@已删除用户'

            def resolve_role(id: int) -> str:
                return '@已删除身份组'

        if self.fix_channel_mentions and ctx.guild:

            def resolve_channel(id: int) -> str:
                c = ctx.guild.get_channel(id)
                return f'#{c.name}' if c else '#已删除频道'

        else:

            def resolve_channel(id: int) -> str:
                return f'<#{id}>'

        transforms = {
            '@': resolve_member,
            '@!': resolve_member,
            '#': resolve_channel,
            '@&': resolve_role,
        }

        def repl(match: re.Match) -> str:
            type = match[1]
            id = int(match[2])
            transformed = transforms[type](id)
            return transformed

        result = re.sub(r'<(@[!&]?|#)([0-9]{15,20})>', repl, argument)
        if self.escape_markdown:
            result = qq.utils.escape_markdown(result)
        elif self.remove_markdown:
            result = qq.utils.remove_markdown(result)

        # Completely ensure no mentions escape:
        return qq.utils.escape_mentions(result)


class Greedy(List[T]):
    r"""一个特殊的转换器，贪婪地消耗参数，直到它不能。
    由于这种行为，大多数输入错误都被悄悄丢弃，因为它被用作何时停止解析的指示器。

    当遇到解析器错误时，贪婪转换器停止转换，撤消内部字符串解析例程，并继续定期解析。

    例如，在以下代码中：

    .. code-block:: python3

        @commands.command()
        async def test(ctx, numbers: Greedy[int], reason: str):
            await ctx.send("numbers: {}, reason: {}".format(numbers, reason))

    调用 ``[p]test 1 2 3 4 5 6 hello`` 会传递 ``numbers`` 为 ``[1, 2, 3, 4, 5, 6]`` 和 ``reason`` 为 ``hello``\.

    有关更多信息，请查看 :ref:`ext_commands_special_converters`。
    """

    __slots__ = ('converter',)

    def __init__(self, *, converter: T):
        self.converter = converter

    def __repr__(self):
        converter = getattr(self.converter, '__name__', repr(self.converter))
        return f'Greedy[{converter}]'

    def __class_getitem__(cls, params: Union[Tuple[T], T]) -> Greedy[T]:
        if not isinstance(params, tuple):
            params = (params,)
        if len(params) != 1:
            raise TypeError('Greedy[...] 只接受一个参数')
        converter = params[0]

        origin = getattr(converter, '__origin__', None)
        args = getattr(converter, '__args__', ())

        if not (callable(converter) or isinstance(converter, Converter) or origin is not None):
            raise TypeError('Greedy[...] 需要一个类型或一个 Converter 实例。')

        if converter in (str, type(None)) or origin is Greedy:
            raise TypeError(f'Greedy[{converter.__name__}] 无效。')

        if origin is Union and type(None) in args:
            raise TypeError(f'Greedy[{converter!r}] 无效。')

        return cls(converter=converter)


def _convert_to_bool(argument: str) -> bool:
    lowered = argument.lower()
    if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on', '开', '打开', '启用', '是', '真'):
        return True
    elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off', '关', '关闭', '禁用', '否', '假'):
        return False
    else:
        raise BadBoolArgument(lowered)


def get_converter(param: inspect.Parameter) -> Any:
    converter = param.annotation
    if converter is param.empty:
        if param.default is not param.empty:
            converter = str if param.default is None else type(param.default)
        else:
            converter = str
    return converter


_GenericAlias = type(List[T])


def is_generic_type(tp: Any, *, _GenericAlias: Type = _GenericAlias) -> bool:
    return isinstance(tp, type) and issubclass(tp, Generic) or isinstance(tp, _GenericAlias)  # type: ignore


CONVERTER_MAPPING: Dict[Type[Any], Any] = {
    qq.Object: ObjectConverter,
    qq.Member: MemberConverter,
    qq.User: UserConverter,
    qq.Message: MessageConverter,
    qq.PartialMessage: PartialMessageConverter,
    qq.TextChannel: TextChannelConverter,
    qq.Guild: GuildConverter,
    qq.Role: RoleConverter,
    qq.Colour: ColourConverter,
    qq.VoiceChannel: VoiceChannelConverter,
    qq.CategoryChannel: CategoryChannelConverter,
    qq.abc.GuildChannel: GuildChannelConverter,
}


async def _actual_conversion(ctx: Context, converter, argument: str, param: inspect.Parameter):
    if converter is bool:
        return _convert_to_bool(argument)

    try:
        module = converter.__module__
    except AttributeError:
        pass
    else:
        if module is not None and (module.startswith('qq.') and not module.endswith('converter')):
            converter = CONVERTER_MAPPING.get(converter, converter)

    try:
        if inspect.isclass(converter) and issubclass(converter, Converter):
            if inspect.ismethod(converter.convert):
                return await converter.convert(ctx, argument)
            else:
                return await converter().convert(ctx, argument)
        elif isinstance(converter, Converter):
            return await converter.convert(ctx, argument)
    except CommandError:
        raise
    except Exception as exc:
        raise ConversionError(converter, exc) from exc

    try:
        return converter(argument)
    except CommandError:
        raise
    except Exception as exc:
        try:
            name = converter.__name__
        except AttributeError:
            name = converter.__class__.__name__

        raise BadArgument(f'参数“{param.name}”转换为“{name}”失败。') from exc


async def run_converters(ctx: Context, converter, argument: str, param: inspect.Parameter):
    """|coro|

    为给定的转换器、参数和参数运行转换器。

    此函数执行的工作与库在后台执行的工作相同。

    Parameters
    ------------
    ctx: :class:`Context`
        在其下运行转换器的调用 context 。
    converter: Any
        要运行的转换器，这对应于函数中的注释。
    argument: :class:`str`
        要转换为的参数。
    param: :class:`inspect.Parameter`
        被转换的参数。这主要用于错误报告。

    Raises
    -------
    CommandError
        转换器无法转换。

    Returns
    --------
    Any
        由此产生的转换。
    """
    origin = getattr(converter, '__origin__', None)

    if origin is Union:
        errors = []
        _NoneType = type(None)
        union_args = converter.__args__
        for conv in union_args:
            # if we got to this part in the code, then the previous conversions have failed
            # so we should just undo the view, return the default, and allow parsing to continue
            # with the other parameters
            if conv is _NoneType and param.kind != param.VAR_POSITIONAL:
                ctx.view.undo()
                return None if param.default is param.empty else param.default

            try:
                value = await run_converters(ctx, conv, argument, param)
            except CommandError as exc:
                errors.append(exc)
            else:
                return value

        # if we're here, then we failed all the converters
        raise BadUnionArgument(param, union_args, errors)

    if origin is Literal:
        errors = []
        conversions = {}
        literal_args = converter.__args__
        for literal in literal_args:
            literal_type = type(literal)
            try:
                value = conversions[literal_type]
            except KeyError:
                try:
                    value = await _actual_conversion(ctx, literal_type, argument, param)
                except CommandError as exc:
                    errors.append(exc)
                    conversions[literal_type] = object()
                    continue
                else:
                    conversions[literal_type] = value

            if value == literal:
                return value

        # if we're here, then we failed to match all the literals
        raise BadLiteralArgument(param, literal_args, errors)

    # This must be the last if-clause in the chain of origin checking
    # Nearly every type is a generic type within the typing library
    # So care must be taken to make sure a more specialised origin handle
    # isn't overwritten by the widest if clause
    if origin is not None and is_generic_type(converter):
        converter = origin

    return await _actual_conversion(ctx, converter, argument, param)
