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

from typing import Optional, Any, TYPE_CHECKING, List, Callable, Type, Tuple, Union

from qq.error import ClientException, QQException
from ... import Role

if TYPE_CHECKING:
    from inspect import Parameter

    from .converter import Converter
    from .context import Context
    from .cooldowns import Cooldown, BucketType
    from .flags import Flag
    from qq.abc import GuildChannel

__all__ = (
    'CommandError',
    'MissingRequiredArgument',
    'BadArgument',
    'PrivateMessageOnly',
    'NoPrivateMessage',
    'CheckFailure',
    'CheckAnyFailure',
    'CommandNotFound',
    'DisabledCommand',
    'CommandInvokeError',
    'TooManyArguments',
    'UserInputError',
    'CommandOnCooldown',
    'MaxConcurrencyReached',
    'NotOwner',
    'MessageNotFound',
    'ObjectNotFound',
    'MemberNotFound',
    'GuildNotFound',
    'UserNotFound',
    'ChannelNotFound',
    'ChannelNotReadable',
    'BadColourArgument',
    'BadColorArgument',
    'RoleNotFound',
    'BadBoolArgument',
    'MissingRole',
    'BotMissingRole',
    'MissingAnyRole',
    'BotMissingAnyRole',
    'MissingPermissions',
    'BotMissingPermissions',
    'ConversionError',
    'BadUnionArgument',
    'BadLiteralArgument',
    'ArgumentParsingError',
    'UnexpectedQuoteError',
    'InvalidEndOfQuotedStringError',
    'ExpectedClosingQuoteError',
    'ExtensionError',
    'ExtensionAlreadyLoaded',
    'ExtensionNotLoaded',
    'NoEntryPointError',
    'ExtensionFailed',
    'ExtensionNotFound',
    'CommandRegistrationError',
    'FlagError',
    'BadFlagArgument',
    'MissingFlagArgument',
    'TooManyFlags',
    'MissingRequiredFlag',
    'InvalidSetupArguments'
)


class CommandError(QQException):
    r"""????????????????????????????????????????????????

    ???????????? :exc:`qq.QQException`???

    ??????????????????????????????????????????????????????????????????????????????????????????????????? :class:`.Bot`\, :func:`.on_command_error` ????????????????????????????????????
    """

    def __init__(self, message: Optional[str] = None, *args: Any) -> None:
        if message is not None:
            # clean-up @everyone and @here mentions
            m = message.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')
            super().__init__(m, *args)
        else:
            super().__init__(*args)


class ConversionError(CommandError):
    """??? Converter ???????????? CommandError ??????????????????

    ???????????? :exc:`CommandError` ???

    Attributes
    ----------
    converter: :class:`qq.ext.commands.Converter`
        ?????????????????????
    original: :exc:`Exception`
        ???????????????????????? ?????????????????? ``__cause__`` ????????????????????????
    """

    def __init__(self, converter: Converter, original: Exception) -> None:
        self.converter: Converter = converter
        self.original: Exception = original


class UserInputError(CommandError):
    """?????????????????????????????????????????????????????????

    ???????????? :exc:`CommandError`???
    """
    pass


class CommandNotFound(CommandError):
    """?????????????????????????????????????????????????????????????????????

    ????????????????????????????????????????????????????????????????????????????????????

    ???????????? :exc:`CommandError` ???
    """
    pass


class MissingRequiredArgument(UserInputError):
    """???????????????????????????????????????????????????????????????

    ???????????? :exc:`UserInputError`

    Attributes
    -----------
    param: :class:`inspect.Parameter`
        ???????????????
    """

    def __init__(self, param: Parameter) -> None:
        self.param: Parameter = param
        super().__init__(f'{param.name} ???????????????????????????')


class TooManyArguments(UserInputError):
    """??????????????????????????????????????? :attr:`.Command.ignore_extra` ?????????????????? ``True`` ??????????????????

    ???????????? :exc:`UserInputError`
    """
    pass


class BadArgument(UserInputError):
    """???????????????????????????????????????????????????????????????????????????

    ???????????? :exc:`UserInputError`
    """
    pass


class CheckFailure(CommandError):
    """??? :attr:`.Command.checks` ??????????????????????????????????????????

    ???????????? :exc:`CommandError`
    """
    pass


class CheckAnyFailure(CheckFailure):
    """??? :func:`check_any` ???????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`???

    Attributes
    ------------
    errors: List[:class:`CheckFailure`]
        ????????????????????????????????????
    checks: List[Callable[[:class:`Context`], :class:`bool`]]
        ????????????????????????????????????
    """

    def __init__(self, checks: List[CheckFailure], errors: List[Callable[[Context], bool]]) -> None:
        self.checks: List[CheckFailure] = checks
        self.errors: List[Callable[[Context], bool]] = errors
        super().__init__('???????????????????????????')


class PrivateMessageOnly(CheckFailure):
    """?????????????????????????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`
    """

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or '??????????????????????????????')


class NoPrivateMessage(CheckFailure):
    """??????????????????????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`
    """

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or '??????????????????????????????')


class NotOwner(CheckFailure):
    """????????????????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`
    """
    pass


class ObjectNotFound(BadArgument):
    """????????????????????? ID ?????????????????????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        ????????????????????????????????????
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'{argument!r} ?????????????????? ID ??????????????????')


class MemberNotFound(BadArgument):
    """??????????????????????????????????????????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        ?????????????????????????????????
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'??????????????????{argument}??????')


class GuildNotFound(BadArgument):
    """??????????????????????????????????????????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        ???????????????????????????????????????
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'??????????????????{argument}??????')


class UserNotFound(BadArgument):
    """?????????????????????????????????????????????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        ????????????????????????????????????
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'??????????????????{argument}??????')


class MessageNotFound(BadArgument):
    """??????????????????????????????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        ????????????????????????????????????
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'??????????????????{argument}??????')


class ChannelNotReadable(BadArgument):
    """???????????????????????????????????????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: Union[:class:`.abc.GuildChannel`, :class:`.Thread`]
        ???????????????????????????????????????
    """

    def __init__(self, argument: Union[GuildChannel]) -> None:
        self.argument: Union[GuildChannel] = argument
        super().__init__(f"???????????? {argument.mention} ???????????????")


class ChannelNotFound(BadArgument):
    """????????????????????????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        ???????????????????????????????????????
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'?????????????????????{argument}??????')


class BadColourArgument(BadArgument):
    """??????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        ??????????????????????????????
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'?????????{argument}????????????')


BadColorArgument = BadColourArgument


class RoleNotFound(BadArgument):
    """????????????????????????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        ???????????????????????????????????????
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'?????????????????????{argument}??????')


class BadBoolArgument(BadArgument):
    """?????????????????????????????????????????????

    ???????????? :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        ?????????????????????????????????????????????????????????
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'{argument} ???????????????????????????')


class DisabledCommand(CommandError):
    """?????????????????????????????????????????????

    ???????????? :exc:`CommandError`
    """
    pass


class CommandInvokeError(CommandError):
    """????????????????????????????????????????????????

    ???????????? :exc:`CommandError`

    Attributes
    -----------
    original: :exc:`Exception`
        ???????????????????????? ?????????????????? ``__cause__`` ????????????????????????
    """

    def __init__(self, e: Exception) -> None:
        self.original: Exception = e
        super().__init__(f'Command raised an exception: {e.__class__.__name__}: {e}')


class CommandOnCooldown(CommandError):
    """?????????????????????????????????????????????????????????

    ???????????? :exc:`CommandError`

    Attributes
    -----------
    cooldown: :class:`.Cooldown`
        ???????????? ``rate`` ??? ``per`` ???????????????????????? :func:`.cooldown` ????????????
    type: :class:`BucketType`
        ?????????????????????????????????
    retry_after: :class:`float`
        ??????????????????????????????????????????
    """

    def __init__(self, cooldown: Cooldown, retry_after: float, type: BucketType) -> None:
        self.cooldown: Cooldown = cooldown
        self.retry_after: float = retry_after
        self.type: BucketType = type
        super().__init__(f'????????????????????? ??? {retry_after:.2f}s ?????????')


class MaxConcurrencyReached(CommandError):
    """????????????????????????????????????????????????????????????

    Attributes
    ------------
    number: :class:`int`
        ????????????????????????????????????
    per: :class:`.BucketType`
        ????????? :func:`.max_concurrency` ????????????????????????
    """

    def __init__(self, number: int, per: BucketType) -> None:
        self.number: int = number
        self.per: BucketType = per
        name = per.name
        suffix = '??? %s' % name if per.name != 'default' else 'globally'
        plural = '%s %s ???'
        fmt = plural % (suffix, number)
        super().__init__(f'????????????????????????????????? ???????????? {fmt} ???????????????')


class MissingRole(CheckFailure):
    """??????????????????????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`

    .. versionadded:: 1.1

    Attributes
    -----------
    missing_role: Union[:class:`str`, :class:`int`]
        ???????????????????????????
        ??????????????? :func:`~.commands.has_role` ????????????
    """

    def __init__(self, missing_role: Role) -> None:
        self.missing_role: Role = missing_role
        message = f'?????????????????????????????? {missing_role!r}???'
        super().__init__(message)


class BotMissingRole(CheckFailure):
    """?????????????????????????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`

    Attributes
    -----------
    missing_role: Union[:class:`str`, :class:`int`]
        ???????????????????????????
        ??????????????? :func:`~.commands.has_role` ????????????
    """

    def __init__(self, missing_role: Role) -> None:
        self.missing_role: Role = missing_role
        message = f'Bot ??????????????? {missing_role!r} ?????????????????????'
        super().__init__(message)


class MissingAnyRole(CheckFailure):
    """????????????????????????????????????????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`

    Attributes
    -----------
    missing_roles: List[Union[:class:`str`, :class:`int`]]
        ??????????????????????????????
        ?????????????????? :func:`~.commands.has_any_role` ????????????
    """

    def __init__(self, missing_roles: Role) -> None:
        self.missing_roles: Role = missing_roles

        missing = [f"'{role}'" for role in missing_roles]

        if len(missing) > 2:
            fmt = '{}, or {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' or '.join(missing)

        message = f"??????????????????????????????????????????{fmt}"
        super().__init__(message)


class BotMissingAnyRole(CheckFailure):
    """?????????????????????????????????????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`

    Attributes
    -----------
    missing_roles: List[Union[:class:`str`, :class:`int`]]
        ????????????????????????????????????
        ?????????????????? :func:`~.commands.has_any_role` ????????????

    """

    def __init__(self, missing_roles: List[Role]) -> None:
        self.missing_roles: List[Role] = missing_roles

        missing = [f"'{role}'" for role in missing_roles]

        if len(missing) > 2:
            fmt = '{}, or {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' or '.join(missing)

        message = f"Bot ???????????????????????????????????????{fmt}"
        super().__init__(message)


class MissingPermissions(CheckFailure):
    """???????????????????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`

    Attributes
    -----------
    missing_permissions: List[:class:`str`]
        ????????????????????????
    """

    def __init__(self, missing_permissions: List[str], *args: Any) -> None:
        self.missing_permissions: List[str] = missing_permissions

        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in missing_permissions]

        if len(missing) > 2:
            fmt = '{}, and {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        message = f'??????????????????????????? {fmt} ?????????'
        super().__init__(message, *args)


class BotMissingPermissions(CheckFailure):
    """??????????????????????????????????????????????????????????????????

    ???????????? :exc:`CheckFailure`

    Attributes
    -----------
    missing_permissions: List[:class:`str`]
        ????????????????????????
    """

    def __init__(self, missing_permissions: List[str], *args: Any) -> None:
        self.missing_permissions: List[str] = missing_permissions

        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in missing_permissions]

        if len(missing) > 2:
            fmt = '{}, and {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        message = f'Bot ?????? {fmt} ??????????????????????????????'
        super().__init__(message, *args)


class BadUnionArgument(UserInputError):
    """??? :data:`typing.Union` ?????????????????????????????????????????????????????????

    ???????????? :exc:`UserInputError`

    Attributes
    -----------
    param: :class:`inspect.Parameter`
        ????????????????????????
    converters: Tuple[Type, ``...``]
        ????????????????????????????????????????????????
    errors: List[:class:`CommandError`]
        ?????????????????????????????????????????????
    """

    def __init__(self, param: Parameter, converters: Tuple[Type, ...], errors: List[CommandError]) -> None:
        self.param: Parameter = param
        self.converters: Tuple[Type, ...] = converters
        self.errors: List[CommandError] = errors

        def _get_name(x):
            try:
                return x.__name__
            except AttributeError:
                if hasattr(x, '__origin__'):
                    return repr(x)
                return x.__class__.__name__

        to_string = [_get_name(x) for x in converters]
        if len(to_string) > 2:
            fmt = '{}, or {}'.format(', '.join(to_string[:-1]), to_string[-1])
        else:
            fmt = ' or '.join(to_string)

        super().__init__(f'????????????{param.name}???????????? {fmt}???')


class BadLiteralArgument(UserInputError):
    """??? :data:`typing.Literal` ??????????????????????????????????????????????????????

    ???????????? :exc:`UserInputError`

    Attributes
    -----------
    param: :class:`inspect.Parameter`
        ????????????????????????
    literals: Tuple[Any, ``...``]
        ????????????????????????????????????????????????
    errors: List[:class:`CommandError`]
        ?????????????????????????????????????????????
    """

    def __init__(self, param: Parameter, literals: Tuple[Any, ...], errors: List[CommandError]) -> None:
        self.param: Parameter = param
        self.literals: Tuple[Any, ...] = literals
        self.errors: List[CommandError] = errors

        to_string = [repr(l) for l in literals]
        if len(to_string) > 2:
            fmt = '{}, or {}'.format(', '.join(to_string[:-1]), to_string[-1])
        else:
            fmt = ' or '.join(to_string)

        super().__init__(f'????????????{param.name}?????????????????? {fmt}???')


class ArgumentParsingError(UserInputError):
    """?????????????????????????????????????????????????????????

    ???????????? :exc:`UserInputError`???

    ?????????????????? i18n ???????????????????????????????????????
    """
    pass


class UnexpectedQuoteError(ArgumentParsingError):
    """??????????????????????????????????????????????????????????????????

    ???????????? :exc:`ArgumentParsingError`???

    Attributes
    ------------
    quote: :class:`str`
        ??????????????????????????????????????????
    """

    def __init__(self, quote: str) -> None:
        self.quote: str = quote
        super().__init__(f'???????????????????????????????????? {quote!r}')


class InvalidEndOfQuotedStringError(ArgumentParsingError):
    """???????????????????????????????????????????????????????????????????????????????????????

    ???????????? :exc:`ArgumentParsingError`???

    Attributes
    -----------
    char: :class:`str`
        ?????????????????????????????????????????????
    """

    def __init__(self, char: str) -> None:
        self.char: str = char
        super().__init__(f'??????????????????????????????????????? {char!r}')


class ExpectedClosingQuoteError(ArgumentParsingError):
    """???????????????????????????????????????????????????

    ???????????? :exc:`ArgumentParsingError`???

    Attributes
    -----------
    close_quote: :class:`str`
        ????????????????????????
    """

    def __init__(self, close_quote: str) -> None:
        self.close_quote: str = close_quote
        super().__init__(f'???????????? {close_quote}???')


class ExtensionError(QQException):
    """????????????????????????????????????

    ???????????? :exc:`~qq.QQException`???

    Attributes
    ------------
    name: :class:`str`
        ?????????????????????
    """

    def __init__(self, message: Optional[str] = None, *args: Any, name: str) -> None:
        self.name: str = name
        message = message or f'?????? {name!r} ????????????'
        # clean-up @everyone and @here mentions
        m = message.replace('@everyone', '@\u200beveryone')
        super().__init__(m, *args)


class ExtensionAlreadyLoaded(ExtensionError):
    """????????????????????????????????????

    ???????????? :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f'?????? {name!r} ????????????', name=name)


class ExtensionNotLoaded(ExtensionError):
    """????????????????????????????????????

    ???????????? :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f'?????? {name!r} ???????????????', name=name)


class NoEntryPointError(ExtensionError):
    """??????????????? ``setup`` ?????????????????????????????????

    ???????????? :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"?????? {name!r} ?????????setup??? ?????????", name=name)


class InvalidSetupArguments(ExtensionError):
    """??????????????????????????? ``kwargs`` ??? ``kwargs`` ????????????``setup`` ????????????????????????

    ???????????? :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"?????? {name!r} ????????????kwargs?????????????????????kwargs??????", name=name)


class ExtensionFailed(ExtensionError):
    """?????????????????? ``setup`` ??????????????????????????????????????????????????????

    ???????????? :exc:`ExtensionError`

    Attributes
    -----------
    name: :class:`str`
        ????????????????????????
    original: :exc:`Exception`
        ???????????????????????? ?????????????????? ``__cause__`` ????????????????????????
    """

    def __init__(self, name: str, original: Exception) -> None:
        self.original: Exception = original
        msg = f'?????? {name!r} ???????????????{original.__class__.__name__}???{original}'
        super().__init__(msg, name=name)


class ExtensionNotFound(ExtensionError):
    """????????????????????????????????????

    ???????????? :exc:`ExtensionError`

    Attributes
    -----------
    name: :class:`str`
        ????????????????????????
    """

    def __init__(self, name: str) -> None:
        msg = f'?????????????????? {name!r}???'
        super().__init__(msg, name=name)


class CommandRegistrationError(ClientException):
    """???????????????????????????????????????????????????????????????????????????

    ???????????? :exc:`qq.ClientException`

    Attributes
    ----------
    name: :class:`str`
        ??????????????????????????????
    alias_conflict: :class:`bool`
        ???????????????????????????????????????????????????????????????
    """

    def __init__(self, name: str, *, alias_conflict: bool = False) -> None:
        self.name: str = name
        self.alias_conflict: bool = alias_conflict
        type_ = 'alias' if alias_conflict else 'command'
        super().__init__(f'{type_} {name} ??????????????????????????????????????????')


class FlagError(BadArgument):
    """??????????????????????????????????????????????????????

    ???????????? :exc:`BadArgument`???
    """
    pass


class TooManyFlags(FlagError):
    """?????????????????????????????????????????????

    ???????????? :exc:`FlagError`???

    Attributes
    ------------
    flag: :class:`~qq.ext.commands.Flag`
        ???????????????????????????
    values: List[:class:`str`]
        ???????????????
    """

    def __init__(self, flag: Flag, values: List[str]) -> None:
        self.flag: Flag = flag
        self.values: List[str] = values
        super().__init__(f'??????????????????????????? {flag.max_args}???????????? {len(values)}???')


class BadFlagArgument(FlagError):
    """??????????????????????????????????????????

    ???????????? :exc:`FlagError`???

    Attributes
    -----------
    flag: :class:`~qq.ext.commands.Flag`
        ????????????????????????
    """

    def __init__(self, flag: Flag) -> None:
        self.flag: Flag = flag
        try:
            name = flag.annotation.__name__
        except AttributeError:
            name = flag.annotation.__class__.__name__

        super().__init__(f'??????????????? {flag.name!r} ????????? {name!r}')


class MissingRequiredFlag(FlagError):
    """???????????????????????????????????????

    ???????????? :exc:`FlagError`

    Attributes
    -----------
    flag: :class:`~qq.ext.commands.Flag`
        ???????????????????????????
    """

    def __init__(self, flag: Flag) -> None:
        self.flag: Flag = flag
        super().__init__(f'?????? {flag.name!r} ?????????????????????')


class MissingFlagArgument(FlagError):
    """???????????????????????????????????????

    ???????????? :exc:`FlagError`

    Attributes
    -----------
    flag: :class:`~qq.ext.commands.Flag`
        ????????????????????????
    """

    def __init__(self, flag: Flag) -> None:
        self.flag: Flag = flag
        super().__init__(f'?????? {flag.name!r} ????????????')
