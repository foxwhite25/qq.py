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
    r"""所有命令相关错误的基本异常类型。

    这继承自 :exc:`qq.QQException`。

    这个异常和从它继承的异常以一种特殊的方式被处理，因为它们被捕获并从 :class:`.Bot`\, :func:`.on_command_error` 传递到一个特殊的事件中。
    """

    def __init__(self, message: Optional[str] = None, *args: Any) -> None:
        if message is not None:
            # clean-up @everyone and @here mentions
            m = message.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')
            super().__init__(m, *args)
        else:
            super().__init__(*args)


class ConversionError(CommandError):
    """当 Converter 类引发非 CommandError 时引发异常。

    这继承自 :exc:`CommandError` 。

    Attributes
    ----------
    converter: :class:`qq.ext.commands.Converter`
        失败的转换器。
    original: :exc:`Exception`
        引发的原始异常。 你也可以通过 ``__cause__`` 属性获取此信息。
    """

    def __init__(self, converter: Converter, original: Exception) -> None:
        self.converter: Converter = converter
        self.original: Exception = original


class UserInputError(CommandError):
    """涉及用户输入错误的错误的基本异常类型。

    这继承自 :exc:`CommandError`。
    """
    pass


class CommandNotFound(CommandError):
    """尝试调用命令但未找到该名称下的命令时引发异常。

    这不是针对无效子命令引发的，而只是尝试调用的初始主命令。

    这继承自 :exc:`CommandError` 。
    """
    pass


class MissingRequiredArgument(UserInputError):
    """解析命令时引发异常，并且未遇到所需的参数。

    这继承自 :exc:`UserInputError`

    Attributes
    -----------
    param: :class:`inspect.Parameter`
        缺少参数。
    """

    def __init__(self, param: Parameter) -> None:
        self.param: Parameter = param
        super().__init__(f'{param.name} 是缺少的必需参数。')


class TooManyArguments(UserInputError):
    """当命令传递了太多参数并且其 :attr:`.Command.ignore_extra` 属性未设置为 ``True`` 时引发异常。

    这继承自 :exc:`UserInputError`
    """
    pass


class BadArgument(UserInputError):
    """在传递给命令的参数上遇到解析或转换失败时引发异常。

    这继承自 :exc:`UserInputError`
    """
    pass


class CheckFailure(CommandError):
    """当 :attr:`.Command.checks` 中的检查函数失败时引发异常。

    这继承自 :exc:`CommandError`
    """
    pass


class CheckAnyFailure(CheckFailure):
    """当 :func:`check_any` 中的所有检查函数都失败时引发异常。

    这继承自 :exc:`CheckFailure`。

    Attributes
    ------------
    errors: List[:class:`CheckFailure`]
        执行期间捕获的错误列表。
    checks: List[Callable[[:class:`Context`], :class:`bool`]]
        失败的检查检查函数列表。
    """

    def __init__(self, checks: List[CheckFailure], errors: List[Callable[[Context], bool]]) -> None:
        self.checks: List[CheckFailure] = checks
        self.errors: List[Callable[[Context], bool]] = errors
        super().__init__('你无权运行此命令。')


class PrivateMessageOnly(CheckFailure):
    """当操作在私人消息上下文之外不起作用时引发异常。

    这继承自 :exc:`CheckFailure`
    """

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or '该命令只能用于私信。')


class NoPrivateMessage(CheckFailure):
    """当操作在私人消息上下文中不起作用时引发异常。

    这继承自 :exc:`CheckFailure`
    """

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or '该命令不能用于私信。')


class NotOwner(CheckFailure):
    """当消息作者不是机器人的所有者时引发异常。

    这继承自 :exc:`CheckFailure`
    """
    pass


class ObjectNotFound(BadArgument):
    """当提供的参数与 ID 或提及的格式不匹配时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        调用者提供的不匹配的参数
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'{argument!r} 不遵循有效的 ID 或提及格式。')


class MemberNotFound(BadArgument):
    """在机器人的缓存中找不到提供的成员时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        未找到调用者提供的成员
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'未找到成员“{argument}”。')


class GuildNotFound(BadArgument):
    """在机器人的缓存中找不到提供的频道时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        未找到的调用者提供的频道未
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'未找到频道“{argument}”。')


class UserNotFound(BadArgument):
    """当在机器人的缓存中找不到提供的用户时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        未找到的调用者提供的用户
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'未找到用户“{argument}”。')


class MessageNotFound(BadArgument):
    """在频道中找不到提供的消息时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        未找到的调用者提供的消息
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'未找到消息“{argument}”。')


class ChannelNotReadable(BadArgument):
    """当机器人无权读取子频道中的消息时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: Union[:class:`.abc.GuildChannel`, :class:`.Thread`]
        调用者提供的不可读的子频道
    """

    def __init__(self, argument: Union[GuildChannel]) -> None:
        self.argument: Union[GuildChannel] = argument
        super().__init__(f"无法阅读 {argument.mention} 中的消息。")


class ChannelNotFound(BadArgument):
    """当机器人找不到子频道时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        未找到的调用者提供的子频道
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'未找到子频道“{argument}”。')


class BadColourArgument(BadArgument):
    """颜色无效时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        调用者提供的颜色无效
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'颜色“{argument}”无效。')


BadColorArgument = BadColourArgument


class RoleNotFound(BadArgument):
    """当机器人找不到身份组时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        未找到的调用者提供的身份组
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'未找到身份组“{argument}”。')


class BadBoolArgument(BadArgument):
    """当布尔参数不可转换时引发异常。

    这继承自 :exc:`BadArgument`

    Attributes
    -----------
    argument: :class:`str`
        调用者提供的不在预定义列表中的布尔参数
    """

    def __init__(self, argument: str) -> None:
        self.argument: str = argument
        super().__init__(f'{argument} 不是认识的布尔选项')


class DisabledCommand(CommandError):
    """调用正在禁用的命令时引发异常。

    这继承自 :exc:`CommandError`
    """
    pass


class CommandInvokeError(CommandError):
    """当被调用的命令引发异常时的异常。

    这继承自 :exc:`CommandError`

    Attributes
    -----------
    original: :exc:`Exception`
        引发的原始异常。 你也可以通过 ``__cause__`` 属性获取此信息。
    """

    def __init__(self, e: Exception) -> None:
        self.original: Exception = e
        super().__init__(f'Command raised an exception: {e.__class__.__name__}: {e}')


class CommandOnCooldown(CommandError):
    """当被调用的命令处于冷却状态时引发异常。

    这继承自 :exc:`CommandError`

    Attributes
    -----------
    cooldown: :class:`.Cooldown`
        一个具有 ``rate`` 和 ``per`` 属性的类，类似于 :func:`.cooldown` 装饰器。
    type: :class:`BucketType`
        与冷却时间关联的类型。
    retry_after: :class:`float`
        在你可以重试之前等待的秒数。
    """

    def __init__(self, cooldown: Cooldown, retry_after: float, type: BucketType) -> None:
        self.cooldown: Cooldown = cooldown
        self.retry_after: float = retry_after
        self.type: BucketType = type
        super().__init__(f'你正在冷却中。 在 {retry_after:.2f}s 后重试')


class MaxConcurrencyReached(CommandError):
    """当被调用的命令达到其最大并发时引发异常。

    Attributes
    ------------
    number: :class:`int`
        允许的最大并发调用者数。
    per: :class:`.BucketType`
        传递给 :func:`.max_concurrency` 装饰器的桶类型。
    """

    def __init__(self, number: int, per: BucketType) -> None:
        self.number: int = number
        self.per: BucketType = per
        name = per.name
        suffix = '每 %s' % name if per.name != 'default' else 'globally'
        plural = '%s %s 次'
        fmt = plural % (suffix, number)
        super().__init__(f'太多人在使用这个命令。 它只能在 {fmt} 同时使用。')


class MissingRole(CheckFailure):
    """当命令调用者缺少运行命令的身份组时引发异常。

    这继承自 :exc:`CheckFailure`

    .. versionadded:: 1.1

    Attributes
    -----------
    missing_role: Union[:class:`str`, :class:`int`]
        缺少的必需身份组。
        这是传递给 :func:`~.commands.has_role` 的参数。
    """

    def __init__(self, missing_role: Role) -> None:
        self.missing_role: Role = missing_role
        message = f'运行此命令需要身份组 {missing_role!r}。'
        super().__init__(message)


class BotMissingRole(CheckFailure):
    """当机器人的成员缺乏运行命令的身份组时引发异常。

    这继承自 :exc:`CheckFailure`

    Attributes
    -----------
    missing_role: Union[:class:`str`, :class:`int`]
        缺少的必需身份组。
        这是传递给 :func:`~.commands.has_role` 的参数。
    """

    def __init__(self, missing_role: Role) -> None:
        self.missing_role: Role = missing_role
        message = f'Bot 需要身份组 {missing_role!r} 才能运行此命令'
        super().__init__(message)


class MissingAnyRole(CheckFailure):
    """当命令调用者缺少指定用于运行命令的任何身份组时引发异常。

    这继承自 :exc:`CheckFailure`

    Attributes
    -----------
    missing_roles: List[Union[:class:`str`, :class:`int`]]
        调用者缺少的身份组。
        这些是传递给 :func:`~.commands.has_any_role` 的参数。
    """

    def __init__(self, missing_roles: Role) -> None:
        self.missing_roles: Role = missing_roles

        missing = [f"'{role}'" for role in missing_roles]

        if len(missing) > 2:
            fmt = '{}, or {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' or '.join(missing)

        message = f"你至少缺少一个必需的身份组：{fmt}"
        super().__init__(message)


class BotMissingAnyRole(CheckFailure):
    """当机器人的成员缺少指定运行命令的任何身份组时引发异常。

    这继承自 :exc:`CheckFailure`

    Attributes
    -----------
    missing_roles: List[Union[:class:`str`, :class:`int`]]
        缺少机器人成员的身份组。
        这些是传递给 :func:`~.commands.has_any_role` 的参数。

    """

    def __init__(self, missing_roles: List[Role]) -> None:
        self.missing_roles: List[Role] = missing_roles

        missing = [f"'{role}'" for role in missing_roles]

        if len(missing) > 2:
            fmt = '{}, or {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' or '.join(missing)

        message = f"Bot 缺少至少一个必需的身份组：{fmt}"
        super().__init__(message)


class MissingPermissions(CheckFailure):
    """当命令调用者缺乏运行命令的权限时引发异常。

    这继承自 :exc:`CheckFailure`

    Attributes
    -----------
    missing_permissions: List[:class:`str`]
        缺少所需的权限。
    """

    def __init__(self, missing_permissions: List[str], *args: Any) -> None:
        self.missing_permissions: List[str] = missing_permissions

        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in missing_permissions]

        if len(missing) > 2:
            fmt = '{}, and {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        message = f'你缺少运行此命令的 {fmt} 权限。'
        super().__init__(message, *args)


class BotMissingPermissions(CheckFailure):
    """当机器人的成员缺乏运行命令的权限时引发异常。

    这继承自 :exc:`CheckFailure`

    Attributes
    -----------
    missing_permissions: List[:class:`str`]
        缺少所需的权限。
    """

    def __init__(self, missing_permissions: List[str], *args: Any) -> None:
        self.missing_permissions: List[str] = missing_permissions

        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in missing_permissions]

        if len(missing) > 2:
            fmt = '{}, and {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        message = f'Bot 需要 {fmt} 权限才能运行此命令。'
        super().__init__(message, *args)


class BadUnionArgument(UserInputError):
    """当 :data:`typing.Union` 转换器对其所有关联类型失败时引发异常。

    这继承自 :exc:`UserInputError`

    Attributes
    -----------
    param: :class:`inspect.Parameter`
        转换失败的参数。
    converters: Tuple[Type, ``...``]
        按失败顺序尝试转换的转换器元组。
    errors: List[:class:`CommandError`]
        由于转换失败而捕获的错误列表。
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

        super().__init__(f'无法将“{param.name}”转换为 {fmt}。')


class BadLiteralArgument(UserInputError):
    """当 :data:`typing.Literal` 转换器的所有关联值都失败时引发异常。

    这继承自 :exc:`UserInputError`

    Attributes
    -----------
    param: :class:`inspect.Parameter`
        转换失败的参数。
    literals: Tuple[Any, ``...``]
        按失败顺序在转换中比较的一组值。
    errors: List[:class:`CommandError`]
        由于转换失败而捕获的错误列表。
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

        super().__init__(f'无法将“{param.name}”转换为文字 {fmt}。')


class ArgumentParsingError(UserInputError):
    """当解析器无法解析用户的输入时引发异常。

    这继承自 :exc:`UserInputError`。

    有一些子类为 i18n 目的实现更细度的解析错误。
    """
    pass


class UnexpectedQuoteError(ArgumentParsingError):
    """当解析器在非引用字符串中遇到引号时引发异常。

    这继承自 :exc:`ArgumentParsingError`。

    Attributes
    ------------
    quote: :class:`str`
        在非引号字符串中找到的引号。
    """

    def __init__(self, quote: str) -> None:
        self.quote: str = quote
        super().__init__(f'非引号字符串中的意外引号 {quote!r}')


class InvalidEndOfQuotedStringError(ArgumentParsingError):
    """当字符串中的结束引号后需要空格但发现不同的字符时引发异常。

    这继承自 :exc:`ArgumentParsingError`。

    Attributes
    -----------
    char: :class:`str`
        找到的字符而不是预期的字符串。
    """

    def __init__(self, char: str) -> None:
        self.char: str = char
        super().__init__(f'结束引号后的预期空格但收到 {char!r}')


class ExpectedClosingQuoteError(ArgumentParsingError):
    """当需要引号字符但未找到时引发异常。

    这继承自 :exc:`ArgumentParsingError`。

    Attributes
    -----------
    close_quote: :class:`str`
        预期的引号字符。
    """

    def __init__(self, close_quote: str) -> None:
        self.close_quote: str = close_quote
        super().__init__(f'预计关闭 {close_quote}。')


class ExtensionError(QQException):
    """扩展相关错误的基本异常。

    这继承自 :exc:`~qq.QQException`。

    Attributes
    ------------
    name: :class:`str`
        有错误的扩展。
    """

    def __init__(self, message: Optional[str] = None, *args: Any, name: str) -> None:
        self.name: str = name
        message = message or f'扩展 {name!r} 有错误。'
        # clean-up @everyone and @here mentions
        m = message.replace('@everyone', '@\u200beveryone')
        super().__init__(m, *args)


class ExtensionAlreadyLoaded(ExtensionError):
    """已加载扩展时引发的异常。

    这继承自 :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f'扩展 {name!r} 已加载。', name=name)


class ExtensionNotLoaded(ExtensionError):
    """未加载扩展时引发的异常。

    这继承自 :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f'扩展 {name!r} 尚未加载。', name=name)


class NoEntryPointError(ExtensionError):
    """当扩展没有 ``setup`` 入口点函数时引发异常。

    这继承自 :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"扩展 {name!r} 没有“setup” 函数。", name=name)


class InvalidSetupArguments(ExtensionError):
    """当扩展包含一个除了 ``kwargs`` 但 ``kwargs`` 被传递的``setup`` 函数时引发异常。

    这继承自 :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"扩展 {name!r} 不采用“kwargs”，但给出了“kwargs”。", name=name)


class ExtensionFailed(ExtensionError):
    """在执行模块或 ``setup`` 入口点期间无法加载扩展时引发的异常。

    这继承自 :exc:`ExtensionError`

    Attributes
    -----------
    name: :class:`str`
        出现错误的扩展。
    original: :exc:`Exception`
        引发的原始异常。 你也可以通过 ``__cause__`` 属性获取此信息。
    """

    def __init__(self, name: str, original: Exception) -> None:
        self.original: Exception = original
        msg = f'扩展 {name!r} 引发错误：{original.__class__.__name__}：{original}'
        super().__init__(msg, name=name)


class ExtensionNotFound(ExtensionError):
    """找不到扩展时引发的异常。

    这继承自 :exc:`ExtensionError`

    Attributes
    -----------
    name: :class:`str`
        出现错误的扩展。
    """

    def __init__(self, name: str) -> None:
        msg = f'无法加载扩展 {name!r}。'
        super().__init__(msg, name=name)


class CommandRegistrationError(ClientException):
    """由于名称已被其他命令采用而无法添加命令时引发异常。

    这继承自 :exc:`qq.ClientException`

    Attributes
    ----------
    name: :class:`str`
        出现错误的命令名称。
    alias_conflict: :class:`bool`
        冲突的名称是否是我们尝试添加的命令的别名。
    """

    def __init__(self, name: str, *, alias_conflict: bool = False) -> None:
        self.name: str = name
        self.alias_conflict: bool = alias_conflict
        type_ = 'alias' if alias_conflict else 'command'
        super().__init__(f'{type_} {name} 已经是一个现有的命令或别名。')


class FlagError(BadArgument):
    """所有标志解析相关错误的基本异常类型。

    这继承自 :exc:`BadArgument`。
    """
    pass


class TooManyFlags(FlagError):
    """当标志接收到太多值时引发异常。

    这继承自 :exc:`FlagError`。

    Attributes
    ------------
    flag: :class:`~qq.ext.commands.Flag`
        收到太多值的标志。
    values: List[:class:`str`]
        传递的值。
    """

    def __init__(self, flag: Flag, values: List[str]) -> None:
        self.flag: Flag = flag
        self.values: List[str] = values
        super().__init__(f'标志值太多，预期为 {flag.max_args}，但收到 {len(values)}。')


class BadFlagArgument(FlagError):
    """当标志无法转换值时引发异常。

    这继承自 :exc:`FlagError`。

    Attributes
    -----------
    flag: :class:`~qq.ext.commands.Flag`
        转换失败的标志。
    """

    def __init__(self, flag: Flag) -> None:
        self.flag: Flag = flag
        try:
            name = flag.annotation.__name__
        except AttributeError:
            name = flag.annotation.__class__.__name__

        super().__init__(f'无法为标志 {flag.name!r} 转换为 {name!r}')


class MissingRequiredFlag(FlagError):
    """未给出所需标志时引发异常。

    这继承自 :exc:`FlagError`

    Attributes
    -----------
    flag: :class:`~qq.ext.commands.Flag`
        未找到所需的标志。
    """

    def __init__(self, flag: Flag) -> None:
        self.flag: Flag = flag
        super().__init__(f'标记 {flag.name!r} 是必需的且缺失')


class MissingFlagArgument(FlagError):
    """标志未获得值时引发的异常。

    这继承自 :exc:`FlagError`

    Attributes
    -----------
    flag: :class:`~qq.ext.commands.Flag`
        未获得值的标志。
    """

    def __init__(self, flag: Flag) -> None:
        self.flag: Flag = flag
        super().__init__(f'标志 {flag.name!r} 没有参数')
