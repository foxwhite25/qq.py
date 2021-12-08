from __future__ import annotations

import re
import inspect
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
    """The base class of custom converters that require the :class:`.Context`
    to be passed to be useful.
    This allows you to implement converters that function similar to the
    special cased ``qq`` classes.
    Classes that derive from this should override the :meth:`~.Converter.convert`
    method to do its conversion logic. This method must be a :ref:`coroutine <coroutine>`.
    """

    async def convert(self, ctx: Context, argument: str) -> T_co:
        """|coro|
        The method to override to do conversion logic.
        If an error is found while converting, it is recommended to
        raise a :exc:`.CommandError` derived exception as it will
        properly propagate to the error handlers.
        Parameters
        -----------
        ctx: :class:`.Context`
            The invocation context that the argument is being used in.
        argument: :class:`str`
            The argument that is being converted.
        Raises
        -------
        :exc:`.CommandError`
            A generic exception occurred when converting the argument.
        :exc:`.BadArgument`
            The converter failed to convert the argument.
        """
        raise NotImplementedError('Derived classes need to implement this.')


_ID_REGEX = re.compile(r'([0-9]{15,20})$')


class IDConverter(Converter[T_co]):
    @staticmethod
    def _get_id_match(argument):
        return _ID_REGEX.match(argument)


class ObjectConverter(IDConverter[qq.Object]):
    """Converts to a :class:`~qq.Object`.
    The argument must follow the valid ID or mention formats (e.g. `<@80088516616269824>`).
    .. versionadded:: 2.0
    The lookup strategy is as follows (in order):
    1. Lookup by ID.
    2. Lookup by member, role, or channel mention.
    """

    async def convert(self, ctx: Context, argument: str) -> qq.Object:
        match = self._get_id_match(argument) or re.match(r'<(?:@(?:!|&)?|#)([0-9]{15,20})>$', argument)

        if match is None:
            raise ObjectNotFound(argument)

        result = int(match.group(1))

        return qq.Object(id=result)


class MemberConverter(IDConverter[qq.Member]):
    """Converts to a :class:`~qq.Member`.
    All lookups are via the local guild. If in a DM context, then the lookup
    is done by the global cache.
    The lookup strategy is as follows (in order):
    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discrim
    4. Lookup by name
    5. Lookup by nickname
    .. versionchanged:: 1.5
         Raise :exc:`.MemberNotFound` instead of generic :exc:`.BadArgument`
    .. versionchanged:: 1.5.1
        This converter now lazily fetches members from the gateway and HTTP APIs,
        optionally caching the result if :attr:`.MemberCacheFlags.joined` is enabled.
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
        if ws.is_ratelimited():
            # If we're being rate limited on the WS, then fall back to using the HTTP API
            # So we don't have to wait ~60 seconds for the query to finish
            try:
                member = await guild.fetch_member(user_id)
            except qq.HTTPException:
                return None

            if cache:
                guild._add_member(member)
            return member

        # If we're not being rate limited then we can use the websocket to actually query
        members = await guild.query_members(limit=1, user_ids=[user_id], cache=cache)
        if not members:
            return None
        return members[0]

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
                result = guild.get_member(user_id) or _utils_get(ctx.message.mentions, id=user_id)
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
    """Converts to a :class:`~qq.User`.
    All lookups are via the global user cache.
    The lookup strategy is as follows (in order):
    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name#discrim
    4. Lookup by name
    .. versionchanged:: 1.5
         Raise :exc:`.UserNotFound` instead of generic :exc:`.BadArgument`
    .. versionchanged:: 1.6
        This converter now lazily fetches users from the HTTP APIs if an ID is passed
        and it's not available in cache.
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
    """Converts to a :class:`qq.PartialMessage`.
    .. versionadded:: 1.7
    The creation strategy is as follows (in order):
    1. By "{channel ID}-{message ID}" (retrieved by shift-clicking on "Copy ID")
    2. By message ID (The message is assumed to be in the context channel.)
    3. By message URL
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
        channel_id = data.get('channel_id')
        message_id = int(data['message_id'])
        guild_id = data.get('guild_id')
        if guild_id is None:
            guild_id = ctx.guild and ctx.guild.id
        elif guild_id == '@me':
            guild_id = None
        else:
            guild_id = int(guild_id)
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
    """Converts to a :class:`qq.Message`.
    .. versionadded:: 1.1
    The lookup strategy is as follows (in order):
    1. Lookup by "{channel ID}-{message ID}" (retrieved by shift-clicking on "Copy ID")
    2. Lookup by message ID (the message **must** be in the context channel)
    3. Lookup by message URL
    .. versionchanged:: 1.5
         Raise :exc:`.ChannelNotFound`, :exc:`.MessageNotFound` or :exc:`.ChannelNotReadable` instead of generic :exc:`.BadArgument`
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
    """Converts to a :class:`~qq.abc.GuildChannel`.
    All lookups are via the local guild. If in a DM context, then the lookup
    is done by the global cache.
    The lookup strategy is as follows (in order):
    1. Lookup by ID.
    2. Lookup by mention.
    3. Lookup by name.
    .. versionadded:: 2.0
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
    async def convert(self, ctx: Context, argument: str) -> qq.TextChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'text_channels', qq.TextChannel)


class VoiceChannelConverter(IDConverter[qq.VoiceChannel]):
    async def convert(self, ctx: Context, argument: str) -> qq.VoiceChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'voice_channels', qq.VoiceChannel)


class CategoryChannelConverter(IDConverter[qq.CategoryChannel]):
    async def convert(self, ctx: Context, argument: str) -> qq.CategoryChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'categories', qq.CategoryChannel)


class LiveChannelConverter(IDConverter[qq.CategoryChannel]):
    async def convert(self, ctx: Context, argument: str) -> qq.CategoryChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'live_channels', qq.CategoryChannel)


class AppChannelConverter(IDConverter[qq.CategoryChannel]):
    async def convert(self, ctx: Context, argument: str) -> qq.CategoryChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'app_channels', qq.CategoryChannel)


class ThreadChannelConverter(IDConverter[qq.CategoryChannel]):
    async def convert(self, ctx: Context, argument: str) -> qq.CategoryChannel:
        return GuildChannelConverter._resolve_channel(ctx, argument, 'thread_channels', qq.CategoryChannel)


class ColourConverter(Converter[qq.Colour]):
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
    """Converts to a :class:`~qq.Guild`.
    The lookup strategy is as follows (in order):
    1. Lookup by ID.
    2. Lookup by name. (There is no disambiguation for Guilds with multiple matching names).
    .. versionadded:: 1.7
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
                return f'@{m.display_name if self.use_nicknames else m.name}' if m else '@deleted-user'

            def resolve_role(id: int) -> str:
                r = _utils_get(msg.role_mentions, id=id) or ctx.guild.get_role(id)
                return f'@{r.name}' if r else '@deleted-role'

        else:

            def resolve_member(id: int) -> str:
                m = _utils_get(msg.mentions, id=id) or ctx.bot.get_user(id)
                return f'@{m.name}' if m else '@deleted-user'

            def resolve_role(id: int) -> str:
                return '@deleted-role'

        if self.fix_channel_mentions and ctx.guild:

            def resolve_channel(id: int) -> str:
                c = ctx.guild.get_channel(id)
                return f'#{c.name}' if c else '#deleted-channel'

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
            raise TypeError('Greedy[...] only takes a single argument')
        converter = params[0]

        origin = getattr(converter, '__origin__', None)
        args = getattr(converter, '__args__', ())

        if not (callable(converter) or isinstance(converter, Converter) or origin is not None):
            raise TypeError('Greedy[...] expects a type or a Converter instance.')

        if converter in (str, type(None)) or origin is Greedy:
            raise TypeError(f'Greedy[{converter.__name__}] is invalid.')

        if origin is Union and type(None) in args:
            raise TypeError(f'Greedy[{converter!r}] is invalid.')

        return cls(converter=converter)


def _convert_to_bool(argument: str) -> bool:
    lowered = argument.lower()
    if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on'):
        return True
    elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off'):
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

        raise BadArgument(f'Converting to "{name}" failed for parameter "{param.name}".') from exc


async def run_converters(ctx: Context, converter, argument: str, param: inspect.Parameter):
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