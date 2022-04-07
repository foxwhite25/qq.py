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
import datetime
import functools
import inspect
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    Literal,
    List,
    Optional,
    Union,
    Set,
    Tuple,
    TypeVar,
    Type,
    TYPE_CHECKING,
    overload,
)

import qq
from ._types import _BaseCommand
from .cog import Cog
from .context import Context
from .converter import run_converters, get_converter, Greedy
from .cooldowns import Cooldown, BucketType, CooldownMapping, MaxConcurrency, DynamicCooldownMapping
from .errors import *

if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec, TypeGuard

    from qq.message import Message

    from ._types import (
        Coro,
        CoroFunc,
        Check,
        Hook,
        Error,
    )

__all__ = (
    'Command',
    'Group',
    'GroupMixin',
    'command',
    'group',
    'has_role',
    'has_any_role',
    'check',
    'check_any',
    'before_invoke',
    'after_invoke',
    'bot_has_role',
    'bot_has_any_role',
    'cooldown',
    'dynamic_cooldown',
    'max_concurrency',
    'dm_only',
    'guild_only',
    'is_owner',
)

MISSING: Any = qq.utils.MISSING

T = TypeVar('T')
CogT = TypeVar('CogT', bound='Cog')
CommandT = TypeVar('CommandT', bound='Command')
ContextT = TypeVar('ContextT', bound='Context')
# CHT = TypeVar('CHT', bound='Check')
GroupT = TypeVar('GroupT', bound='Group')
HookT = TypeVar('HookT', bound='Hook')
ErrorT = TypeVar('ErrorT', bound='Error')

if TYPE_CHECKING:
    P = ParamSpec('P')
else:
    P = TypeVar('P')


def unwrap_function(function: Callable[..., Any]) -> Callable[..., Any]:
    partial = functools.partial
    while True:
        if hasattr(function, '__wrapped__'):
            function = function.__wrapped__
        elif isinstance(function, partial):
            function = function.func
        else:
            return function


def get_signature_parameters(function: Callable[..., Any], globalns: Dict[str, Any]) -> Dict[str, inspect.Parameter]:
    signature = inspect.signature(function)
    params = {}
    cache: Dict[str, Any] = {}
    eval_annotation = qq.utils.evaluate_annotation
    for name, parameter in signature.parameters.items():
        annotation = parameter.annotation
        if annotation is parameter.empty:
            params[name] = parameter
            continue
        if annotation is None:
            params[name] = parameter.replace(annotation=type(None))
            continue

        annotation = eval_annotation(annotation, globalns, globalns, cache)
        if annotation is Greedy:
            raise TypeError('Unparameterized Greedy[...] is disallowed in signature.')

        params[name] = parameter.replace(annotation=annotation)

    return params


def wrap_callback(coro):
    @functools.wraps(coro)
    async def wrapped(*args, **kwargs):
        try:
            ret = await coro(*args, **kwargs)
        except CommandError:
            raise
        except asyncio.CancelledError:
            return
        except Exception as exc:
            raise CommandInvokeError(exc) from exc
        return ret

    return wrapped


def hooked_wrapped_callback(command, ctx, coro):
    @functools.wraps(coro)
    async def wrapped(*args, **kwargs):
        try:
            ret = await coro(*args, **kwargs)
        except CommandError:
            ctx.command_failed = True
            raise
        except asyncio.CancelledError:
            ctx.command_failed = True
            return
        except Exception as exc:
            ctx.command_failed = True
            raise CommandInvokeError(exc) from exc
        finally:
            if command._max_concurrency is not None:
                await command._max_concurrency.release(ctx)

            await command.call_after_hooks(ctx)
        return ret

    return wrapped


class _CaseInsensitiveDict(dict):
    def __contains__(self, k):
        return super().__contains__(k.casefold())

    def __delitem__(self, k):
        return super().__delitem__(k.casefold())

    def __getitem__(self, k):
        return super().__getitem__(k.casefold())

    def get(self, k, default=None):
        return super().get(k.casefold(), default)

    def pop(self, k, default=None):
        return super().pop(k.casefold(), default)

    def __setitem__(self, k, v):
        super().__setitem__(k.casefold(), v)


class Command(_BaseCommand, Generic[CogT, P, T]):
    r"""一个实现机器人文本命令协议的类。

    这些不是手动创建的，而是通过装饰器或功能接口创建的。

    Attributes
    -----------
    name: :class:`str`
        命令的名称。
    callback: :ref:`coroutine <coroutine>`
        调用命令时执行的协程。
    help: Optional[:class:`str`]
        命令的长帮助文本。
    brief: Optional[:class:`str`]
        命令的简短帮助文本。
    usage: Optional[:class:`str`]
        替换默认帮助文本中的参数。
    aliases: Union[List[:class:`str`], Tuple[:class:`str`]]
        可以在其下调用命令的别名列表。
    enabled: :class:`bool`
        指示当前是否启用命令的布尔值。
        如果命令在禁用时被调用，则 :exc:`.DisabledCommand` 将引发 :func:`.on_command_error` 事件。默认为 ``True`` 。
    parent: Optional[:class:`Group`]
        此命令所属的父组。 ``None`` 如果没有的话。
    cog: Optional[:class:`Cog`]
        该命令所属的齿轮。 ``None`` 如果没有的话。
    checks: List[Callable[[:class:`.Context`], :class:`bool`]]
        一个检查函数列表，用于验证是否可以使用给定的 :class:`.Context` 作为唯一参数来执行命令。
         如果必须抛出异常以表示失败，则应使用继承自 :exc:`.CommandError` 的异常。
         请注意，如果检查失败，则 :exc:`.CheckFailure` 异常将引发到 :func:`.on_command_error` 事件。
    description: :class:`str`
        默认帮助命令中带有前缀的消息。
    hidden: :class:`bool`
        如果为  ``True``\ ，则默认帮助命令不会在帮助输出中显示此内容。
    rest_is_raw: :class:`bool`
        如果 ``False`` 则仅关键字参数，则仅关键字参数将被剥离并处理，
        就好像它是处理 :exc:`.MissingRequiredArgument` 和默认值的常规参数一样，
        而不是传递原始数据。 如果 ``True`` 则仅关键字参数将以完全原始的方式传递其余参数。 默认为 ``False`` 。
    invoked_subcommand: Optional[:class:`Command`]
        调用的子命令（如果有）。
    require_var_positional: :class:`bool`
        如果 ``True`` 并且指定了可变参数位置参数，则要求用户至少指定一个参数。 默认为 ``False`` 。

    ignore_extra: :class:`bool`
        如果 ``True``\，如果它的所有要求都得到满足，则忽略传递给命令的无关字符串
        （例如 ``?foo a b c`` 当只需要 ``a`` 和 ``b`` 时）。
        否则 :func:`.on_command_error` 和本地错误处理程序使用 :exc:`.TooManyArguments` 调用。 默认为 ``True`` 。
    cooldown_after_parsing: :class:`bool`
        如果为 ``True``\，则在参数解析后完成冷却处理，这会调用转换器。 如果 ``False`` 则首先完成冷却处理，然后再调用转换器。 默认为 ``False``  。
    extras: :class:`dict`
        用户的字典提供了附加到命令的附加内容。
        
        .. note::
            该对象可由库复制。

    inherit_hooks: :class:`bool`, default=False
        如果 ``True`` 并且这个命令有一个父 :class:`Group`，那么这个命令将继承所有在 :class:`Group`的检查，``pre_invoke`` 和 ``after_invoke`` 定义。

        .. note::

            在此定义的任何 ``pre_invoke`` 或 ``after_invoke`` 都将覆盖父项。

    """
    __original_kwargs__: Dict[str, Any]

    def __new__(cls: Type[CommandT], *args: Any, **kwargs: Any) -> CommandT:
        # if you're wondering why this is done, it's because we need to ensure
        # we have a complete original copy of **kwargs even for classes that
        # mess with it by popping before delegating to the subclass __init__.
        # In order to do this, we need to control the instance creation and
        # inject the original kwargs through __new__ rather than doing it
        # inside __init__.
        self = super().__new__(cls)

        # we do a shallow copy because it's probably the most common use case.
        # this could potentially break if someone modifies a list or something
        # while it's in movement, but for now this is the cheapest and
        # fastest way to do what we want.
        self.__original_kwargs__ = kwargs.copy()
        return self

    def __init__(self, func: Union[
        Callable[[Concatenate[CogT, ContextT, P]], Coro[T]],
        Callable[[Concatenate[ContextT, P]], Coro[T]],
    ], **kwargs: Any):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError('回调必须是协程。')

        name = kwargs.get('name') or func.__name__
        if not isinstance(name, str):
            raise TypeError('命令的名称必须是字符串。')
        self.name: str = name

        self.callback = func
        self.enabled: bool = kwargs.get('enabled', True)

        help_doc = kwargs.get('help')
        if help_doc is not None:
            help_doc = inspect.cleandoc(help_doc)
        else:
            help_doc = inspect.getdoc(func)
            if isinstance(help_doc, bytes):
                help_doc = help_doc.decode('utf-8')

        self.help: Optional[str] = help_doc

        self.brief: Optional[str] = kwargs.get('brief')
        self.usage: Optional[str] = kwargs.get('usage')
        self.rest_is_raw: bool = kwargs.get('rest_is_raw', False)
        self.aliases: Union[List[str], Tuple[str]] = kwargs.get('aliases', [])
        self.extras: Dict[str, Any] = kwargs.get('extras', {})

        if not isinstance(self.aliases, (list, tuple)):
            raise TypeError("命令的别名必须是一个列表或一个字符串元组。")

        self.description: str = inspect.cleandoc(kwargs.get('description', ''))
        self.hidden: bool = kwargs.get('hidden', False)

        try:
            checks = func.__commands_checks__
            checks.reverse()
        except AttributeError:
            checks = kwargs.get('checks', [])

        self.checks: List[Check] = checks

        try:
            cooldown = func.__commands_cooldown__
        except AttributeError:
            cooldown = kwargs.get('cooldown')

        if cooldown is None:
            buckets = CooldownMapping(cooldown, BucketType.default)
        elif isinstance(cooldown, CooldownMapping):
            buckets = cooldown
        else:
            raise TypeError("Cooldown 必须是 CooldownMapping 或 None 的一个实例。")
        self._buckets: CooldownMapping = buckets

        try:
            max_concurrency = func.__commands_max_concurrency__
        except AttributeError:
            max_concurrency = kwargs.get('max_concurrency')

        self._max_concurrency: Optional[MaxConcurrency] = max_concurrency

        self.require_var_positional: bool = kwargs.get('require_var_positional', False)
        self.ignore_extra: bool = kwargs.get('ignore_extra', True)
        self.cooldown_after_parsing: bool = kwargs.get('cooldown_after_parsing', False)
        self.cog: Optional[CogT] = None

        # bandaid for the fact that sometimes parent can be the bot instance
        parent = kwargs.get('parent')
        self.parent: Optional[GroupMixin] = parent if isinstance(parent, _BaseCommand) else None  # type: ignore

        self._before_invoke: Optional[Hook] = None
        try:
            before_invoke = func.__before_invoke__
        except AttributeError:
            pass
        else:
            self.before_invoke(before_invoke)

        self._after_invoke: Optional[Hook] = None
        try:
            after_invoke = func.__after_invoke__
        except AttributeError:
            pass
        else:
            self.after_invoke(after_invoke)

        # Attempt to bind to parent hooks if applicable
        if not kwargs.get("inherit_hooks", False):
            return

        # We should be binding hooks
        if not self.parent:
            return

        inherited_before_invoke: Optional[Hook] = None
        try:
            inherited_before_invoke = self.parent._before_invoke  # type: ignore
        except AttributeError:
            pass
        else:
            if inherited_before_invoke:
                self.before_invoke(inherited_before_invoke)

        inherited_after_invoke: Optional[Hook] = None
        try:
            inherited_after_invoke = self.parent._after_invoke  # type: ignore
        except AttributeError:
            pass
        else:
            if inherited_after_invoke:
                self.after_invoke(inherited_after_invoke)

        self.checks.extend(self.parent.checks)  # type: ignore

    @property
    def callback(self) -> Union[
        Callable[[Concatenate[CogT, Context, P]], Coro[T]],
        Callable[[Concatenate[Context, P]], Coro[T]],
    ]:
        return self._callback

    @callback.setter
    def callback(self, function: Union[
        Callable[[Concatenate[CogT, Context, P]], Coro[T]],
        Callable[[Concatenate[Context, P]], Coro[T]],
    ]) -> None:
        self._callback = function
        unwrap = unwrap_function(function)
        self.module = unwrap.__module__

        try:
            globalns = unwrap.__globals__
        except AttributeError:
            globalns = {}

        self.params = get_signature_parameters(function, globalns)

    def add_check(self, func: Check) -> None:
        """向命令添加检查。

        这是 :func:`.check` 的非装饰器接口。


        Parameters
        -----------
        func
            将用作检查的函数。
        """

        self.checks.append(func)

    def remove_check(self, func: Check) -> None:
        """从命令中删除检查。

        此函数是幂等的，如果该函数不在命令的检查中，则不会引发异常。

        Parameters
        -----------
        func
            要从检查中删除的函数。
        """

        try:
            self.checks.remove(func)
        except ValueError:
            pass

    def update(self, **kwargs: Any) -> None:
        """使用更新的属性更新 :class:`Command` 实例。

        这在参数方面与 :func:`.command` 装饰器类似，因为它们被传递给 :class:`Command` 或子类构造函数，没有名称和回调。
        """
        self.__init__(self.callback, **dict(self.__original_kwargs__, **kwargs))

    async def __call__(self, context: Context, *args: P.args, **kwargs: P.kwargs) -> T:
        """|coro|

        调用命令持有的内部回调。

        .. note::

            这绕过了所有机制——包括检查、转换器、调用钩子、冷却等。你必须小心地将正确的参数和类型传递给这个函数。
        """
        if self.cog is not None:
            return await self.callback(self.cog, context, *args, **kwargs)  # type: ignore
        else:
            return await self.callback(context, *args, **kwargs)  # type: ignore

    def _ensure_assignment_on_copy(self, other: CommandT) -> CommandT:
        other._before_invoke = self._before_invoke
        other._after_invoke = self._after_invoke
        if self.checks != other.checks:
            other.checks = self.checks.copy()
        if self._buckets.valid and not other._buckets.valid:
            other._buckets = self._buckets.copy()
        if self._max_concurrency != other._max_concurrency:
            # _max_concurrency won't be None at this point
            other._max_concurrency = self._max_concurrency.copy()  # type: ignore

        try:
            other.on_error = self.on_error
        except AttributeError:
            pass
        return other

    def copy(self: CommandT) -> CommandT:
        """创建此命令的副本。

        Returns
        --------
        :class:`Command`
            此命令的新实例。
        """
        ret = self.__class__(self.callback, **self.__original_kwargs__)
        return self._ensure_assignment_on_copy(ret)

    def _update_copy(self: CommandT, kwargs: Dict[str, Any]) -> CommandT:
        if kwargs:
            kw = kwargs.copy()
            kw.update(self.__original_kwargs__)
            copy = self.__class__(self.callback, **kw)
            return self._ensure_assignment_on_copy(copy)
        else:
            return self.copy()

    async def dispatch_error(self, ctx: Context, error: Exception) -> None:
        ctx.command_failed = True
        cog = self.cog
        try:
            coro = self.on_error
        except AttributeError:
            pass
        else:
            injected = wrap_callback(coro)
            if cog is not None:
                await injected(cog, ctx, error)
            else:
                await injected(ctx, error)

        try:
            if cog is not None:
                local = Cog._get_overridden_method(cog.cog_command_error)
                if local is not None:
                    wrapped = wrap_callback(local)
                    await wrapped(ctx, error)
        finally:
            ctx.bot.dispatch('command_error', ctx, error)

    async def transform(self, ctx: Context, param: inspect.Parameter) -> Any:
        required = param.default is param.empty
        converter = get_converter(param)
        consume_rest_is_special = param.kind == param.KEYWORD_ONLY and not self.rest_is_raw
        view = ctx.view
        view.skip_ws()

        # The greedy converter is simple -- it keeps going until it fails in which case,
        # it undos the view ready for the next parameter to use instead
        if isinstance(converter, Greedy):
            if param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY):
                return await self._transform_greedy_pos(ctx, param, required, converter.converter)
            elif param.kind == param.VAR_POSITIONAL:
                return await self._transform_greedy_var_pos(ctx, param, converter.converter)
            else:
                # if we're here, then it's a KEYWORD_ONLY param type
                # since this is mostly useless, we'll helpfully transform Greedy[X]
                # into just X and do the parsing that way.
                converter = converter.converter

        if view.eof:
            if param.kind == param.VAR_POSITIONAL:
                raise RuntimeError()  # break the loop
            if required:
                if self._is_typing_optional(param.annotation):
                    return None
                if hasattr(converter, '__commands_is_flag__') and converter._can_be_constructible():
                    return await converter._construct_default(ctx)
                raise MissingRequiredArgument(param)
            return param.default

        previous = view.index
        if consume_rest_is_special:
            argument = view.read_rest().strip()
        else:
            try:
                argument = view.get_quoted_word()
            except ArgumentParsingError as exc:
                if self._is_typing_optional(param.annotation):
                    view.index = previous
                    return None
                else:
                    raise exc
        view.previous = previous

        # type-checker fails to narrow argument
        return await run_converters(ctx, converter, argument, param)  # type: ignore

    async def _transform_greedy_pos(self, ctx: Context, param: inspect.Parameter, required: bool,
                                    converter: Any) -> Any:
        view = ctx.view
        result = []
        while not view.eof:
            # for use with a manual undo
            previous = view.index

            view.skip_ws()
            try:
                argument = view.get_quoted_word()
                value = await run_converters(ctx, converter, argument, param)  # type: ignore
            except (CommandError, ArgumentParsingError):
                view.index = previous
                break
            else:
                result.append(value)

        if not result and not required:
            return param.default
        return result

    async def _transform_greedy_var_pos(self, ctx: Context, param: inspect.Parameter, converter: Any) -> Any:
        view = ctx.view
        previous = view.index
        try:
            argument = view.get_quoted_word()
            value = await run_converters(ctx, converter, argument, param)  # type: ignore
        except (CommandError, ArgumentParsingError):
            view.index = previous
            raise RuntimeError() from None  # break loop
        else:
            return value

    @property
    def clean_params(self) -> Dict[str, inspect.Parameter]:
        """Dict[:class:`str`, :class:`inspect.Parameter`]:
        检索没有上下文或自身参数的参数字典。

        用于检查签名。
        """
        result = self.params.copy()
        if self.cog is not None:
            # first parameter is self
            try:
                del result[next(iter(result))]
            except StopIteration:
                raise ValueError("缺少 'self' 参数") from None

        try:
            # first/second parameter is context
            del result[next(iter(result))]
        except StopIteration:
            raise ValueError("缺少 'context' 参数") from None

        return result

    @property
    def full_parent_name(self) -> str:
        """:class:`str`: 检索完全限定的父命令名称。

        这是执行它所需的基本命令名称。 例如，在 ``?one two three``  中，父名称将是 ``one two``  。
        """
        entries = []
        command = self
        # command.parent is type-hinted as GroupMixin some attributes are resolved via MRO
        while command.parent is not None:  # type: ignore
            command = command.parent  # type: ignore
            entries.append(command.name)  # type: ignore

        return ' '.join(reversed(entries))

    @property
    def parents(self) -> List[Group]:
        """List[:class:`Group`]: 检索此命令的父级。

        如果该命令没有父级，则它返回一个空的 :class:`list`。

        例如在命令 ``?a b c test`` 中，父级是 ``[c, b, a]``。
        """
        entries = []
        command = self
        while command.parent is not None:  # type: ignore
            command = command.parent  # type: ignore
            entries.append(command)

        return entries

    @property
    def root_parent(self) -> Optional[Group]:
        """Optional[:class:`Group`]: 检索此命令的根父级。

        如果该命令没有父级，则返回 ``None`` 。

        例如在命令 ``?a b c test`` 中，根父节点是 ``a`` 。
        """
        if not self.parent:
            return None
        return self.parents[-1]

    @property
    def qualified_name(self) -> str:
        """:class:`str`: 检索完全限定的命令名称。

        这也是带有命令名称的完整父名称。 例如，在 ``?one two three`` 中，限定名称将是 ``one two three`` 。
        """

        parent = self.full_parent_name
        if parent:
            return parent + ' ' + self.name
        else:
            return self.name

    def __str__(self) -> str:
        return self.qualified_name

    async def _parse_arguments(self, ctx: Context) -> None:
        ctx.args = [ctx] if self.cog is None else [self.cog, ctx]
        ctx.kwargs = {}
        args = ctx.args
        kwargs = ctx.kwargs

        view = ctx.view
        iterator = iter(self.params.items())

        if self.cog is not None:
            # we have 'self' as the first parameter so just advance
            # the iterator and resume parsing
            try:
                next(iterator)
            except StopIteration:
                raise qq.ClientException(f'{self.name} 命令的回调缺少 "self" 参数。')

        # next we have the 'ctx' as the next parameter
        try:
            next(iterator)
        except StopIteration:
            raise qq.ClientException(f'{self.name} 命令的回调缺少 "ctx" 参数。')

        for name, param in iterator:
            ctx.current_parameter = param
            if param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY):
                transformed = await self.transform(ctx, param)
                args.append(transformed)
            elif param.kind == param.KEYWORD_ONLY:
                # kwarg only param denotes "consume rest" semantics
                if self.rest_is_raw:
                    converter = get_converter(param)
                    argument = view.read_rest()
                    kwargs[name] = await run_converters(ctx, converter, argument, param)
                else:
                    kwargs[name] = await self.transform(ctx, param)
                break
            elif param.kind == param.VAR_POSITIONAL:
                if view.eof and self.require_var_positional:
                    raise MissingRequiredArgument(param)
                while not view.eof:
                    try:
                        transformed = await self.transform(ctx, param)
                        args.append(transformed)
                    except RuntimeError:
                        break

        if not self.ignore_extra and not view.eof:
            raise TooManyArguments(f'传递给{self.qualified_name}的参数太多')

    async def call_before_hooks(self, ctx: Context) -> None:
        # now that we're done preparing we can call the pre-command hooks
        # first, call the command local hook:
        cog = self.cog
        if self._before_invoke is not None:
            # should be cog if @commands.before_invoke is used
            instance = getattr(self._before_invoke, '__self__', cog)
            # __self__ only exists for methods, not functions
            # however, if @command.before_invoke is used, it will be a function
            if instance:
                await self._before_invoke(instance, ctx)  # type: ignore
            else:
                await self._before_invoke(ctx)  # type: ignore

        # call the cog local hook if applicable:
        if cog is not None:
            hook = Cog._get_overridden_method(cog.cog_before_invoke)
            if hook is not None:
                await hook(ctx)

        # call the bot global hook if necessary
        hook = ctx.bot._before_invoke
        if hook is not None:
            await hook(ctx)

    async def call_after_hooks(self, ctx: Context) -> None:
        cog = self.cog
        if self._after_invoke is not None:
            instance = getattr(self._after_invoke, '__self__', cog)
            if instance:
                await self._after_invoke(instance, ctx)  # type: ignore
            else:
                await self._after_invoke(ctx)  # type: ignore

        # call the cog local hook if applicable:
        if cog is not None:
            hook = Cog._get_overridden_method(cog.cog_after_invoke)
            if hook is not None:
                await hook(ctx)

        hook = ctx.bot._after_invoke
        if hook is not None:
            await hook(ctx)

    def _prepare_cooldowns(self, ctx: Context) -> None:
        if self._buckets.valid:
            dt = ctx.message.edited_at or ctx.message.created_at
            current = dt.replace(tzinfo=datetime.timezone.utc).timestamp()
            bucket = self._buckets.get_bucket(ctx.message, current)
            if bucket is not None:
                retry_after = bucket.update_rate_limit(current)
                if retry_after:
                    raise CommandOnCooldown(bucket, retry_after, self._buckets.type)  # type: ignore

    async def prepare(self, ctx: Context) -> None:
        ctx.command = self

        if not await self.can_run(ctx):
            raise CheckFailure(f'命令 {self.qualified_name} 的检查函数失败。')

        if self._max_concurrency is not None:
            # For this application, context can be duck-typed as a Message
            await self._max_concurrency.acquire(ctx)  # type: ignore

        try:
            if self.cooldown_after_parsing:
                await self._parse_arguments(ctx)
                self._prepare_cooldowns(ctx)
            else:
                self._prepare_cooldowns(ctx)
                await self._parse_arguments(ctx)

            await self.call_before_hooks(ctx)
        except:
            if self._max_concurrency is not None:
                await self._max_concurrency.release(ctx)  # type: ignore
            raise

    def is_on_cooldown(self, ctx: Context) -> bool:
        """检查命令当前是否处于冷却状态。

        Parameters
        -----------
        ctx: :class:`.Context`
            检查命令冷却状态时使用的调用上下文。

        Returns
        --------
        :class:`bool`
            指示命令是否处于冷却状态的布尔值。
        """
        if not self._buckets.valid:
            return False

        bucket = self._buckets.get_bucket(ctx.message)
        dt = ctx.message.edited_at or ctx.message.created_at
        current = dt.replace(tzinfo=datetime.timezone.utc).timestamp()
        return bucket.get_tokens(current) == 0

    def reset_cooldown(self, ctx: Context) -> None:
        """重置此命令的冷却时间。

        Parameters
        -----------
        ctx: :class:`.Context`
            重置冷却时间的调用上下文。
        """
        if self._buckets.valid:
            bucket = self._buckets.get_bucket(ctx.message)
            bucket.reset()

    def get_cooldown_retry_after(self, ctx: Context) -> float:
        """检索可以再次尝试此命令之前的秒数。

        Parameters
        -----------
        ctx: :class:`.Context`
            从中检索冷却时间的调用上下文。

        Returns
        --------
        :class:`float`
            此命令的冷却剩余时间（以秒为单位）。
            如果这是 ``0.0`` ，则该命令不在冷却中。
        """
        if self._buckets.valid:
            bucket = self._buckets.get_bucket(ctx.message)
            dt = ctx.message.edited_at or ctx.message.created_at
            current = dt.replace(tzinfo=datetime.timezone.utc).timestamp()
            return bucket.get_retry_after(current)

        return 0.0

    async def invoke(self, ctx: Context) -> None:
        await self.prepare(ctx)

        # terminate the invoked_subcommand chain.
        # since we're in a regular command (and not a group) then
        # the invoked subcommand is None.
        ctx.invoked_subcommand = None
        ctx.subcommand_passed = None
        injected = hooked_wrapped_callback(self, ctx, self.callback)
        await injected(*ctx.args, **ctx.kwargs)

    async def reinvoke(self, ctx: Context, *, call_hooks: bool = False) -> None:
        ctx.command = self
        await self._parse_arguments(ctx)

        if call_hooks:
            await self.call_before_hooks(ctx)

        ctx.invoked_subcommand = None
        try:
            await self.callback(*ctx.args, **ctx.kwargs)  # type: ignore
        except:
            ctx.command_failed = True
            raise
        finally:
            if call_hooks:
                await self.call_after_hooks(ctx)

    def error(self, coro: ErrorT) -> ErrorT:
        """将协程注册为本地错误处理程序的装饰器。

        本地错误处理程序是一个仅限于单个命令的 :func:`.on_command_error` 事件。
        然而， :func:`.on_command_error` 之后仍然会被调用。

        Parameters
        -----------
        coro: :ref:`coroutine <coroutine>`
            要注册为本地错误处理程序的协程。

        Raises
        -------
        TypeError
            传递的协程实际上并不是协程。
        """

        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('The error handler must be a coroutine.')

        self.on_error: Error = coro
        return coro

    def has_error_handler(self) -> bool:
        """:class:`bool`: 检查命令是否已注册错误处理程序。
        """
        return hasattr(self, 'on_error')

    def before_invoke(self, coro: HookT) -> HookT:
        """将协程注册为调用前钩的装饰器。

        在调用命令之前直接调用调用前钩。 这使得它成为设置数据库连接或所需的任何类型的设置的有用功能。

        这个调用前钩有一个唯一的参数，一个 :class:`.Context`。

        有关更多信息，请参阅 :meth:`.Bot.before_invoke`。

        Parameters
        -----------
        coro: :ref:`coroutine <coroutine>`
            要注册为调用前钩的协程。

        Raises
        -------
        TypeError
            传递的协程实际上并不是协程。
        """
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('调用前钩必须是一个协程。')

        self._before_invoke = coro
        return coro

    def after_invoke(self, coro: HookT) -> HookT:
        """将协程注册为调用后钩的装饰器。

        在调用命令后直接调用后钩。 这使其成为清理数据库连接或任何类型的清理所需的有用功能。

        这个调用后钩有一个唯一的参数，一个 :class:`.Context`。

        有关更多信息，请参阅 :meth:`.Bot.after_invoke`。

        Parameters
        -----------
        coro: :ref:`coroutine <coroutine>`
            要注册为调用后钩的协程。

        Raises
        -------
        TypeError
            传递的协程实际上并不是协程。
        """
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('调用后钩必须是一个协程。')

        self._after_invoke = coro
        return coro

    @property
    def cog_name(self) -> Optional[str]:
        """Optional[:class:`str`]: 此命令所属的 cog 的名称（如果有）。"""
        return type(self.cog).__cog_name__ if self.cog is not None else None

    @property
    def short_doc(self) -> str:
        """:class:`str`: 获取命令的 ``简短`` 文档。

        默认情况下，这是 :attr:`.brief` 属性。
        如果该查找导致空字符串，则使用 :attr:`.help` 属性的第一行。
        """
        if self.brief is not None:
            return self.brief
        if self.help is not None:
            return self.help.split('\n', 1)[0]
        return ''

    def _is_typing_optional(self, annotation: Union[T, Optional[T]]) -> TypeGuard[Optional[T]]:
        return getattr(annotation, '__origin__', None) is Union and type(None) in annotation.__args__  # type: ignore

    @property
    def signature(self) -> str:
        """:class:`str`: 返回对帮助命令输出有用的类似 POSIX 的签名。"""
        if self.usage is not None:
            return self.usage

        params = self.clean_params
        if not params:
            return ''

        result = []
        for name, param in params.items():
            greedy = isinstance(param.annotation, Greedy)
            optional = False  # postpone evaluation of if it's an optional argument

            # for typing.Literal[...], typing.Optional[typing.Literal[...]], and Greedy[typing.Literal[...]], the
            # parameter signature is a literal list of it's values
            annotation = param.annotation.converter if greedy else param.annotation
            origin = getattr(annotation, '__origin__', None)
            if not greedy and origin is Union:
                none_cls = type(None)
                union_args = annotation.__args__
                optional = union_args[-1] is none_cls
                if len(union_args) == 2 and optional:
                    annotation = union_args[0]
                    origin = getattr(annotation, '__origin__', None)

            if origin is Literal:
                name = '|'.join(f'"{v}"' if isinstance(v, str) else str(v) for v in annotation.__args__)
            if param.default is not param.empty:
                # We don't want None or '' to trigger the [name=value] case and instead it should
                # do [name] since [name=None] or [name=] are not exactly useful for the user.
                should_print = param.default if isinstance(param.default, str) else param.default is not None
                if should_print:
                    result.append(f'[{name}={param.default}]' if not greedy else
                                  f'[{name}={param.default}]...')
                    continue
                else:
                    result.append(f'[{name}]')

            elif param.kind == param.VAR_POSITIONAL:
                if self.require_var_positional:
                    result.append(f'<{name}...>')
                else:
                    result.append(f'[{name}...]')
            elif greedy:
                result.append(f'[{name}]...')
            elif optional:
                result.append(f'[{name}]')
            else:
                result.append(f'<{name}>')

        return ' '.join(result)

    async def can_run(self, ctx: Context) -> bool:
        """|coro|

        通过检查 :attr:`~Command.checks` 属性中的所有检查函数来检查命令是否可以执行。 这还会检查命令是否被禁用。

        Parameters
        -----------
        ctx: :class:`.Context`
            当前正在调用的命令的 ctx。

        Raises
        -------
        :class:`CommandError`
            在检查调用期间引发的任何命令错误都将由此函数传播。

        Returns
        --------
        :class:`bool`
            指示是否可以调用命令的布尔值。
        """

        if not self.enabled:
            raise DisabledCommand(f'{self.name} 命令被禁用')

        original = ctx.command
        ctx.command = self

        try:
            if not await ctx.bot.can_run(ctx):
                raise CheckFailure(f'命令 {self.qualified_name} 的全局检查函数失败。')

            cog = self.cog
            if cog is not None:
                local_check = Cog._get_overridden_method(cog.cog_check)
                if local_check is not None:
                    ret = await qq.utils.maybe_coroutine(local_check, ctx)
                    if not ret:
                        return False

            predicates = self.checks
            if not predicates:
                # since we have no checks, then we just return True.
                return True

            return await qq.utils.async_all(predicate(ctx) for predicate in predicates)  # type: ignore
        finally:
            ctx.command = original


class GroupMixin(Generic[CogT]):
    """一个 mixin，它为行为类似于 :class:`.Group` 的类实现通用功能，并允许注册命令。

    Attributes
    -----------
    all_commands: :class:`dict`
        命令名称到 :class:`.Command` 对象的映射。
    case_insensitive: :class:`bool`
        命令是否应该不区分大小写。 默认为 ``False`` 。
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        case_insensitive = kwargs.get('case_insensitive', False)
        self.all_commands: Dict[str, Command[CogT, Any, Any]] = _CaseInsensitiveDict() if case_insensitive else {}
        self.case_insensitive: bool = case_insensitive
        super().__init__(*args, **kwargs)

    @property
    def commands(self) -> Set[Command[CogT, Any, Any]]:
        """Set[:class:`.Command`]: 一组独特的没有注册别名的命令。"""
        return set(self.all_commands.values())

    def recursively_remove_all_commands(self) -> None:
        for command in self.all_commands.copy().values():
            if isinstance(command, GroupMixin):
                command.recursively_remove_all_commands()
            self.remove_command(command.name)

    def add_command(self, command: Command[CogT, Any, Any]) -> None:
        """将 :class:`.Command` 添加到内部命令列表中。

        这通常不被调用，而是使用 :meth:`~.GroupMixin.command` 或 :meth:`~.GroupMixin.group` 快捷装饰器。

        Parameters
        -----------
        command: :class:`Command`
            要添加的命令。

        Raises
        -------
        :exc:`.CommandRegistrationError`
            如果该命令或其别名已被不同的命令注册。
        TypeError
            如果传递的命令不是 :class:`.Command` 的子类。
        """

        if not isinstance(command, Command):
            raise TypeError('传递的命令必须是 Command 的子类')

        if isinstance(self, Command):
            command.parent = self

        if command.name in self.all_commands:
            raise CommandRegistrationError(command.name)

        self.all_commands[command.name] = command
        for alias in command.aliases:
            if alias in self.all_commands:
                self.remove_command(command.name)
                raise CommandRegistrationError(alias, alias_conflict=True)
            self.all_commands[alias] = command

    def remove_command(self, name: str) -> Optional[Command[CogT, Any, Any]]:
        """从内部命令列表中删除 :class:`.Command`。

        这也可以用作删除别名的方法。

        Parameters
        -----------
        name: :class:`str`
            要删除的命令的名称。

        Returns
        --------
        Optional[:class:`.Command`]
            删除的命令。 如果名称无效，则返回 ``None`` 。
        """
        command = self.all_commands.pop(name, None)

        # does not exist
        if command is None:
            return None

        if name in command.aliases:
            # we're removing an alias so we don't want to remove the rest
            return command

        # we're not removing the alias so let's delete the rest of them.
        for alias in command.aliases:
            cmd = self.all_commands.pop(alias, None)
            # in the case of a CommandRegistrationError, an alias might conflict
            # with an already existing command. If this is the case, we want to
            # make sure the pre-existing command is not removed.
            if cmd is not None and cmd != command:
                self.all_commands[alias] = cmd
        return command

    def walk_commands(self) -> Generator[Command[CogT, Any, Any], None, None]:
        """递归遍历所有命令和子命令的迭代器。

        Yields
        ------
        Union[:class:`.Command`, :class:`.Group`]
            来自内部命令列表的命令或组。
        """
        for command in self.commands:
            yield command
            if isinstance(command, GroupMixin):
                yield from command.walk_commands()

    def get_command(self, name: str) -> Optional[Command[CogT, Any, Any]]:
        """从内部命令列表中获取 :class:`.Command` 。

        这也可以用作获取别名的一种方式。

        该名称可以是完全限定的（例如 ``foo bar`` ）将获得组命令 ``foo`` 的子命令 ``bar`` 。
        如果未找到子命令，则像往常一样返回 ``None`` 。

        Parameters
        -----------
        name: :class:`str`
            要获取的命令的名称。

        Returns
        --------
        Optional[:class:`Command`]
            请求的命令。 如果未找到，则返回 ``None`` 。
        """

        # fast path, no space in name.
        if ' ' not in name:
            return self.all_commands.get(name)

        names = name.split()
        if not names:
            return None
        obj = self.all_commands.get(names[0])
        if not isinstance(obj, GroupMixin):
            return obj

        for name in names[1:]:
            try:
                obj = obj.all_commands[name]  # type: ignore
            except (AttributeError, KeyError):
                return None

        return obj

    @overload
    def command(
            self,
            name: str = ...,
            cls: Type[Command[CogT, P, T]] = ...,
            *args: Any,
            **kwargs: Any,
    ) -> Callable[
        [
            Union[
                Callable[[Concatenate[CogT, ContextT, P]], Coro[T]],
                Callable[[Concatenate[ContextT, P]], Coro[T]],
            ]
        ], Command[CogT, P, T]]:
        ...

    @overload
    def command(
            self,
            name: str = ...,
            cls: Type[CommandT] = ...,
            *args: Any,
            **kwargs: Any,
    ) -> Callable[[Callable[[Concatenate[ContextT, P]], Coro[Any]]], CommandT]:
        ...

    def command(
            self,
            name: str = MISSING,
            cls: Type[CommandT] = MISSING,
            *args: Any,
            **kwargs: Any,
    ) -> Callable[[Callable[[Concatenate[ContextT, P]], Coro[Any]]], CommandT]:
        """调用 :func:`.command` 并通过 :meth:`~.GroupMixin.add_command` 将其添加到内部命令列表的快捷方式装饰器。

        Returns
        --------
        Callable[..., :class:`Command`]
            将提供的方法转换为命令的装饰器，将其添加到机器人，然后返回它。
        """

        def decorator(func: Callable[[Concatenate[ContextT, P]], Coro[Any]]) -> CommandT:
            kwargs.setdefault('parent', self)
            result = command(name=name, cls=cls, *args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    @overload
    def group(
            self,
            name: str = ...,
            cls: Type[Group[CogT, P, T]] = ...,
            *args: Any,
            **kwargs: Any,
    ) -> Callable[[
                      Union[
                          Callable[[Concatenate[CogT, ContextT, P]], Coro[T]],
                          Callable[[Concatenate[ContextT, P]], Coro[T]]
                      ]
                  ], Group[CogT, P, T]]:
        ...

    @overload
    def group(
            self,
            name: str = ...,
            cls: Type[GroupT] = ...,
            *args: Any,
            **kwargs: Any,
    ) -> Callable[[Callable[[Concatenate[ContextT, P]], Coro[Any]]], GroupT]:
        ...

    def group(
            self,
            name: str = MISSING,
            cls: Type[GroupT] = MISSING,
            *args: Any,
            **kwargs: Any,
    ) -> Callable[[Callable[[Concatenate[ContextT, P]], Coro[Any]]], GroupT]:
        """调用 :func:`.group` 并通过 :meth:`~.GroupMixin.add_command` 将其添加到内部命令列表的快捷方式装饰器。

        Returns
        --------
        Callable[..., :class:`Group`]
            将提供的方法转换为 Group 的装饰器，将其添加到机器人，然后返回它。
        """

        def decorator(func: Callable[[Concatenate[ContextT, P]], Coro[Any]]) -> GroupT:
            kwargs.setdefault('parent', self)
            result = group(name=name, cls=cls, *args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator


class Group(GroupMixin[CogT], Command[CogT, P, T]):
    """为作为子命令执行的命令实现分组协议的类。

    这个类是 :class:`.Command` 的子类，因此所有在 :class:`.Command` 中有效的选项在这里也有效。

    Attributes
    -----------
    invoke_without_command: :class:`bool`
        指示组回调是否应仅在未找到子命令时才开始解析和调用。
        用于制作一个错误处理函数以告诉用户未找到子命令或在未找到子命令的情况下具有不同的功能。
        如果这是 ``False`` ，则总是首先调用组回调。
        这意味着将执行由其参数指示的检查和解析。 默认为 ``False`` 。
    case_insensitive: :class:`bool`
        指示组的命令是否应不区分大小写。 默认为 ``False`` 。
    """

    def __init__(self, *args: Any, **attrs: Any) -> None:
        self.invoke_without_command: bool = attrs.pop('invoke_without_command', False)
        super().__init__(*args, **attrs)

    def copy(self: GroupT) -> GroupT:
        """创建此 :class:`Group` 的副本。

        Returns
        --------
        :class:`Group`
            组的新实例。
        """
        ret = super().copy()
        for cmd in self.commands:
            ret.add_command(cmd.copy())
        return ret  # type: ignore

    async def invoke(self, ctx: Context) -> None:
        ctx.invoked_subcommand = None
        ctx.subcommand_passed = None
        early_invoke = not self.invoke_without_command
        if early_invoke:
            await self.prepare(ctx)

        view = ctx.view
        previous = view.index
        view.skip_ws()
        trigger = view.get_word()

        if trigger:
            ctx.subcommand_passed = trigger
            ctx.invoked_subcommand = self.all_commands.get(trigger, None)

        if early_invoke:
            injected = hooked_wrapped_callback(self, ctx, self.callback)
            await injected(*ctx.args, **ctx.kwargs)

        ctx.invoked_parents.append(ctx.invoked_with)  # type: ignore

        if trigger and ctx.invoked_subcommand:
            ctx.invoked_with = trigger
            await ctx.invoked_subcommand.invoke(ctx)
        elif not early_invoke:
            # undo the trigger parsing
            view.index = previous
            view.previous = previous
            await super().invoke(ctx)

    async def reinvoke(self, ctx: Context, *, call_hooks: bool = False) -> None:
        ctx.invoked_subcommand = None
        early_invoke = not self.invoke_without_command
        if early_invoke:
            ctx.command = self
            await self._parse_arguments(ctx)

            if call_hooks:
                await self.call_before_hooks(ctx)

        view = ctx.view
        previous = view.index
        view.skip_ws()
        trigger = view.get_word()

        if trigger:
            ctx.subcommand_passed = trigger
            ctx.invoked_subcommand = self.all_commands.get(trigger, None)

        if early_invoke:
            try:
                await self.callback(*ctx.args, **ctx.kwargs)  # type: ignore
            except:
                ctx.command_failed = True
                raise
            finally:
                if call_hooks:
                    await self.call_after_hooks(ctx)

        ctx.invoked_parents.append(ctx.invoked_with)  # type: ignore

        if trigger and ctx.invoked_subcommand:
            ctx.invoked_with = trigger
            await ctx.invoked_subcommand.reinvoke(ctx, call_hooks=call_hooks)
        elif not early_invoke:
            # undo the trigger parsing
            view.index = previous
            view.previous = previous
            await super().reinvoke(ctx, call_hooks=call_hooks)


# Decorators

@overload
def command(
        name: str = ...,
        cls: Type[Command[CogT, P, T]] = ...,
        **attrs: Any,
) -> Callable[
    [
        Union[
            Callable[[Concatenate[CogT, ContextT, P]], Coro[T]],
            Callable[[Concatenate[ContextT, P]], Coro[T]],
        ]
    ]
    , Command[CogT, P, T]]:
    ...


@overload
def command(
        name: str = ...,
        cls: Type[CommandT] = ...,
        **attrs: Any,
) -> Callable[
    [
        Union[
            Callable[[Concatenate[CogT, ContextT, P]], Coro[Any]],
            Callable[[Concatenate[ContextT, P]], Coro[Any]],
        ]
    ]
    , CommandT]:
    ...


def command(
        name: str = MISSING,
        cls: Type[CommandT] = MISSING,
        **attrs: Any
) -> Callable[
    [
        Union[
            Callable[[Concatenate[ContextT, P]], Coro[Any]],
            Callable[[Concatenate[CogT, ContextT, P]], Coro[T]],
        ]
    ]
    , Union[Command[CogT, P, T], CommandT]]:
    """将函数转换为 :class:`.Command` 或如果使用 :func:`.group` 则转为 :class:`.Group` 的装饰器。

    默认情况下，``help`` 属性是从函数的文档字符串中自动接收的，并使用``inspect.cleandoc`` 进行清理。
    如果 docstring 是 ``bytes``，则使用 utf-8 编码将其解码为 :class:`str`。

    所有使用 :func:`.check` 添加的检查都被添加到函数中。 无法通过此装饰器提供你自己的检查。

    Parameters
    -----------
    name: :class:`str`
        用于创建命令的名称。 默认情况下，这使用未更改的函数名称。
    cls
        要构造的类。 默认情况下，这是 :class:`.Command` 。 你通常不会更改此设置。
    attrs
        传递到由 ``cls`` 表示的类的构造中的关键字参数。

    Raises
    -------
    TypeError
        如果函数不是协程或已经是命令。
    """
    if cls is MISSING:
        cls = Command  # type: ignore

    def decorator(func: Union[
        Callable[[Concatenate[ContextT, P]], Coro[Any]],
        Callable[[Concatenate[CogT, ContextT, P]], Coro[Any]],
    ]) -> CommandT:
        if isinstance(func, Command):
            raise TypeError('Callback is already a command.')
        return cls(func, name=name, **attrs)

    return decorator


@overload
def group(
        name: str = ...,
        cls: Type[Group[CogT, P, T]] = ...,
        **attrs: Any,
) -> Callable[
    [
        Union[
            Callable[[Concatenate[CogT, ContextT, P]], Coro[T]],
            Callable[[Concatenate[ContextT, P]], Coro[T]],
        ]
    ]
    , Group[CogT, P, T]]:
    ...


@overload
def group(
        name: str = ...,
        cls: Type[GroupT] = ...,
        **attrs: Any,
) -> Callable[
    [
        Union[
            Callable[[Concatenate[CogT, ContextT, P]], Coro[Any]],
            Callable[[Concatenate[ContextT, P]], Coro[Any]],
        ]
    ]
    , GroupT]:
    ...


def group(
        name: str = MISSING,
        cls: Type[GroupT] = MISSING,
        **attrs: Any,
) -> Callable[
    [
        Union[
            Callable[[Concatenate[ContextT, P]], Coro[Any]],
            Callable[[Concatenate[CogT, ContextT, P]], Coro[T]],
        ]
    ]
    , Union[Group[CogT, P, T], GroupT]]:
    """将函数转换为 :class:`.Group` 的装饰器。

     这类似于 :func:`.command` 装饰器，但 ``cls`` 参数默认设置为 :class:`Group` 。
    """
    if cls is MISSING:
        cls = Group  # type: ignore
    return command(name=name, cls=cls, **attrs)  # type: ignore


def check(predicate: Check) -> Callable[[T], T]:
    r"""向 :class:`.Command` 或其子类添加检查的装饰器。 这些检查可以通过 :attr:`.Command.checks` 访问。

    这些检查应该是接受单个参数的检查函数，参数为 :class:`.Context`。
    如果检查返回类似 ``False``\ 的值，则在调用期间会引发 :exc:`.CheckFailure` 异常并将其发送到 :func:`.on_command_error` 事件。

    如果检查函数中应该抛出异常，那么它应该是 :exc:`.CommandError` 的子类。
    任何不是从它子类化的异常都将被传播，而那些子类将被发送到 :func:`.on_command_error`。

    名为 ``predicate`` 的特殊属性绑定到此装饰器返回的值，以检索传递给装饰器的检查函数。 这允许完成以下内省和链接：

    .. code-block:: python3

        def owner_or_permissions(**perms):
            original = commands.has_permissions(**perms).predicate
            async def extended_check(ctx):
                if ctx.guild is None:
                    return False
                return ctx.guild.owner_id == ctx.author.id or await original(ctx)
            return commands.check(extended_check)

    .. note::

        ``predicate`` 返回的函数 **始终** 是一个协程，即使原始函数不是协程。

    Examples
    ---------

    创建一个基本检查以查看命令调用者是否是你。

    .. code-block:: python3

        def check_if_it_is_me(ctx):
            return ctx.message.author.id == 114514

        @bot.command()
        @commands.check(check_if_it_is_me)
        async def only_for_me(ctx):
            await ctx.send('我知道你!')

    将常见检查转换为装饰器：

    .. code-block:: python3

        def is_me():
            def predicate(ctx):
                return ctx.message.author.id == 114514
            return commands.check(predicate)

        @bot.command()
        @is_me()
        async def only_me(ctx):
            await ctx.send('只有你!')

    Parameters
    -----------
    predicate: Callable[[:class:`Context`], :class:`bool`]
        检查是否应调用命令的检查函数。
    """

    def decorator(func: Union[Command, CoroFunc]) -> Union[Command, CoroFunc]:
        if isinstance(func, Command):
            func.checks.append(predicate)
        else:
            if not hasattr(func, '__commands_checks__'):
                func.__commands_checks__ = []

            func.__commands_checks__.append(predicate)

        return func

    if inspect.iscoroutinefunction(predicate):
        decorator.predicate = predicate
    else:
        @functools.wraps(predicate)
        async def wrapper(ctx):
            return predicate(ctx)  # type: ignore

        decorator.predicate = wrapper

    return decorator  # type: ignore


def check_any(*checks: Check) -> Callable[[T], T]:
    r"""添加了一个 :func:`check` 来检查是否有任何通过的检查会通过，即使用逻辑 OR。

    如果所有检查都失败，则引发 :exc:`.CheckAnyFailure` 以表示失败。 它继承自 :exc:`.CheckFailure`。

    .. note::

        这个函数的 ``predicate`` 属性 **是** 一个协程。

    Parameters
    ------------
    \*checks: Callable[[:class:`Context`], :class:`bool`]
        已用 :func:`check` 装饰器装饰的检查的参数列表。

    Raises
    -------
    TypeError
        通过的检查没有用 :func:`check` 装饰器装饰。

    Examples
    ---------

    创建基本检查以查看它是机器人所有者还是频道所有者：

    .. code-block:: python3

        def is_guild_owner():
            def predicate(ctx):
                return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
            return commands.check(predicate)

        @bot.command()
        @commands.check_any(commands.is_owner(), is_guild_owner())
        async def only_for_owners(ctx):
            await ctx.send('先生你好！')
    """

    unwrapped = []
    for wrapped in checks:
        try:
            pred = wrapped.predicate
        except AttributeError:
            raise TypeError(f'{wrapped!r} 必须由 commands.check 装饰器包装') from None
        else:
            unwrapped.append(pred)

    async def predicate(ctx: Context) -> bool:
        errors = []
        for func in unwrapped:
            try:
                value = await func(ctx)
            except CheckFailure as e:
                errors.append(e)
            else:
                if value:
                    return True
        # if we're here, all checks failed
        raise CheckAnyFailure(unwrapped, errors)

    return check(predicate)


def has_role(item: Union[int, str]) -> Callable[[T], T]:
    """添加的 :func:`.check` 用于检查调用命令的成员是否具有通过指定的名称或 ID 指定的用户组。

    如果指定了字符串，则必须给出用户组的确切名称，包括大写和拼写。

    如果指定了整数，则必须提供用户组的确切 ID。

    如果消息是在私人消息上下文中调用的，则检查将返回 ``False`` 。

    此检查会引发两个特殊异常之一，如果用户缺少用户组，则为 :exc:`.MissingRole`，
    如果在私人消息中使用了 :exc:`.NoPrivateMessage`。
    两者都继承自 :exc:`.CheckFailure`。

    Parameters
    -----------
    item: Union[:class:`int`, :class:`str`]
        要检查的用户组的名称或 ID。
    """

    def predicate(ctx: Context) -> bool:
        if ctx.guild is None:
            raise NoPrivateMessage()

        # ctx.guild is None doesn't narrow ctx.author to Member
        if isinstance(item, int):
            role = qq.utils.get(ctx.author.roles, id=item)  # type: ignore
        else:
            role = qq.utils.get(ctx.author.roles, name=item)  # type: ignore
        if role is None:
            raise MissingRole(item)
        return True

    return check(predicate)


def has_any_role(*items: Union[int, str]) -> Callable[[T], T]:
    r"""A :func:`.check` 添加的内容是检查调用命令的成员是否具有指定的 **任何一个** 用户组。
    这意味着如果他们有指定了三个用户组中的一个，那么此检查将返回 `True`。

    与 :func:`.has_role`\ 类似，传入的名称或ID 必须准确无误。

    此检查会引发两个特殊异常之一，如果用户缺少所有用户组，则为 :exc:`.MissingRole`，
    如果在私人消息中使用了 :exc:`.NoPrivateMessage`。
    两者都继承自 :exc:`.CheckFailure`。

    Parameters
    -----------
    items: List[Union[:class:`str`, :class:`int`]]
        名称或 ID 的参数列表，用于检查成员是否具有用户组。

    Example
    --------

    .. code-block:: python3

        @bot.command()
        @commands.has_any_role('库开发人员', '管理员', 114514)
        async def cool(ctx):
            await ctx.send('你确实很酷')
    """

    def predicate(ctx):
        if ctx.guild is None:
            raise NoPrivateMessage()

        # ctx.guild is None doesn't narrow ctx.author to Member
        getter = functools.partial(qq.utils.get, ctx.author.roles)  # type: ignore
        if any(getter(id=item) is not None if isinstance(item, int) else getter(name=item) is not None for item in
               items):
            return True
        raise MissingAnyRole(list(items))

    return check(predicate)


def bot_has_role(item: int) -> Callable[[T], T]:
    """类似于 :func:`.has_role`，但是是检查机器人本身是否具有用户组。

    此检查会引发两个特殊异常之一，如果机器人缺少用户组，则为 :exc:`.MissingRole`，
    如果在私人消息中使用了 :exc:`.NoPrivateMessage`。
    两者都继承自 :exc:`.CheckFailure`。
    """

    def predicate(ctx):
        if ctx.guild is None:
            raise NoPrivateMessage()

        me = ctx.me
        if isinstance(item, int):
            role = qq.utils.get(me.roles, id=item)
        else:
            role = qq.utils.get(me.roles, name=item)
        if role is None:
            raise BotMissingRole(item)
        return True

    return check(predicate)


def bot_has_any_role(*items: int) -> Callable[[T], T]:
    """类似于 :func:`.has_any_role`，但是是检查机器人本身是否具有任何一个用户组。

    此检查会引发两个特殊异常之一，如果机器人缺少所有用户组，则为 :exc:`.MissingRole`，
    如果在私人消息中使用了 :exc:`.NoPrivateMessage`。
    两者都继承自 :exc:`.CheckFailure`。
    """

    def predicate(ctx):
        if ctx.guild is None:
            raise NoPrivateMessage()

        me = ctx.me
        getter = functools.partial(qq.utils.get, me.roles)
        if any(getter(id=item) is not None if isinstance(item, int) else getter(name=item) is not None for item in
               items):
            return True
        raise BotMissingAnyRole(list(items))

    return check(predicate)


def dm_only() -> Callable[[T], T]:
    """一个 :func:`.check`
    表示这个命令只能在私信上下文中使用。 使用该命令时只允许私信。

    这个检查引发一个特殊的异常， :exc:`.PrivateMessageOnly`，它继承自 :exc:`.CheckFailure`。
    """

    def predicate(ctx: Context) -> bool:
        if not ctx.message.direct:
            raise PrivateMessageOnly()
        return True

    return check(predicate)


def guild_only() -> Callable[[T], T]:
    """一个 :func:`.check` 表示这个命令只能在频道上下文中使用。 基本上，使用该命令时不允许私人消息。

    这个检查引发一个特殊的异常，:exc:`.NoPrivateMessage`，它是从 :exc:`.CheckFailure` 继承而来的。
    """

    def predicate(ctx: Context) -> bool:
        if ctx.message.direct:
            raise NoPrivateMessage()
        return True

    return check(predicate)


def is_owner() -> Callable[[T], T]:
    """一个 :func:`.check` 检查调用此命令的人是否是机器人的所有者。

    这是由 :meth:`.Bot.is_owner` 提供支持的。

    这个检查引发了一个特殊的异常， :exc:`.NotOwner`，它派生自 :exc:`.CheckFailure`。
    """

    async def predicate(ctx: Context) -> bool:
        if not await ctx.bot.is_owner(ctx.author):
            raise NotOwner('你不拥有此机器人。')
        return True

    return check(predicate)


def cooldown(
        rate: int,
        per: float,
        type: Union[BucketType, Callable[[Message], Any]] = BucketType.default
) -> Callable[[T], T]:
    """为 :class:`.Command` 添加冷却时间的装饰器

    冷却时间允许命令在特定时间范围内仅使用特定次数。
    这些冷却时间可以基于每个公会、每个频道、每个用户、
    每个用户组或全局基础。由第三个参数 ``type`` 表示，它必须是枚举类型 :class:`.BucketType`。

    如果冷却被触发，则 :exc:`.CommandOnCooldown` 在 :func:`.on_command_error` 和本地错误处理程序中被触发。

    一个命令只能有一个冷却时间。

    Parameters
    ------------
    rate: :class:`int`
        命令在触发冷却之前可以使用的次数。
    per: :class:`float`
        触发时等待冷却的秒数。
    type: Union[:class:`.BucketType`, Callable[[:class:`.Message`], Any]]
        冷却时间的类型。
    """

    def decorator(func: Union[Command, CoroFunc]) -> Union[Command, CoroFunc]:
        if isinstance(func, Command):
            func._buckets = CooldownMapping(Cooldown(rate, per), type)
        else:
            func.__commands_cooldown__ = CooldownMapping(Cooldown(rate, per), type)
        return func

    return decorator  # type: ignore


def dynamic_cooldown(
        cooldown: Union[BucketType, Callable[[Message], Any]],
        type: BucketType = BucketType.default
) -> Callable[[T], T]:
    """为 :class:`.Command` 添加动态冷却时间的装饰器

    这与 :func:`.cooldown` 的不同之处在于
    它接受一个 :class:`.qq.Message` 类型的单个参数并且必须返回一个 :class:`.Cooldown`
    或 ``None`` 的函数。如果返回 ``None`` ，则该冷却时间被有效绕过。

    冷却时间允许命令在特定时间范围内仅使用特定次数。
    这些冷却时间可以基于每个公会、每个频道、每个用户、每个角色或全局基础。
    由 ``type`` 的第三个参数表示，它必须是枚举类型 :class:`.BucketType` 。

    如果冷却被触发，则 :exc:`.CommandOnCooldown` 在 :func:`.on_command_error` 和本地错误处理程序中被触发。

    一个命令只能有一个冷却时间。

    Parameters
    ------------
    cooldown: Callable[[:class:`.qq.Message`], Optional[:class:`.Cooldown`]]
        一个接收消息并返回冷却时间的函数，该冷却时间将应用于此调用，如果应该绕过冷却时间，则返回 ``None`` 。
    type: :class:`.BucketType`
        冷却时间的类型。
    """
    if not callable(cooldown):
        raise TypeError("必须提供 Callable")

    def decorator(func: Union[Command, CoroFunc]) -> Union[Command, CoroFunc]:
        if isinstance(func, Command):
            func._buckets = DynamicCooldownMapping(cooldown, type)
        else:
            func.__commands_cooldown__ = DynamicCooldownMapping(cooldown, type)
        return func

    return decorator  # type: ignore


def max_concurrency(number: int, per: BucketType = BucketType.default, *, wait: bool = False) -> Callable[[T], T]:
    """为 :class:`.Command` 或其子类添加最大并发的装饰器。

    这使你可以同时只允许一定数量的命令调用，例如，如果命令耗时过长或一次只有一个用户可以使用它。
    这与冷却时间不同，因为没有设定的等待期或令牌桶——只有设定数量的人可以运行命令。

    Parameters
    -------------
    number: :class:`int`
        可以同时运行的此命令的最大调用次数。
    per: :class:`.BucketType`
        此并发所基于的存储桶，例如``BucketType.guild`` 将允许每个公会最多使用 ``number`` 次。
    wait: :class:`bool`
        命令是否应该等待队列结束。
        如果这被设置为 ``False`` 则不是等到命令可以再次运行，该命令会引发 :exc:`.MaxConcurrencyReached` 到其错误处理程序。
        如果这被设置为 ``True`` 则命令会等待直到它可以被执行。
    """

    def decorator(func: Union[Command, CoroFunc]) -> Union[Command, CoroFunc]:
        value = MaxConcurrency(number, per=per, wait=wait)
        if isinstance(func, Command):
            func._max_concurrency = value
        else:
            func.__commands_max_concurrency__ = value
        return func

    return decorator  # type: ignore


def before_invoke(coro) -> Callable[[T], T]:
    """将协程注册为调用前钩的装饰器。

    这允许你在调用钩子之前引用一个不必在同一个齿轮中的几个命令。

    Example
    ---------

    .. code-block:: python3

        async def record_usage(ctx):
            print(ctx.author, 'used', ctx.command)

        @bot.command()
        @commands.before_invoke(record_usage)
        async def who(ctx):
            await ctx.send('我是机器人')

        class What(commands.Cog):

            @commands.command()
            async def where(self, ctx): # Output: <Nothing>
                await ctx.send('在QQ上')

            @commands.command()
            async def why(self, ctx): # Output: <Nothing>
                await ctx.send('因为有人做了我出来')

        bot.add_cog(What())
    """

    def decorator(func: Union[Command, CoroFunc]) -> Union[Command, CoroFunc]:
        if isinstance(func, Command):
            func.before_invoke(coro)
        else:
            func.__before_invoke__ = coro
        return func

    return decorator  # type: ignore


def after_invoke(coro) -> Callable[[T], T]:
    """将协程注册为调用后钩的装饰器。

    这允许你在调用钩子后引用多个命令，这些命令不必位于同一个 cog 中。
    """

    def decorator(func: Union[Command, CoroFunc]) -> Union[Command, CoroFunc]:
        if isinstance(func, Command):
            func.after_invoke(coro)
        else:
            func.__after_invoke__ = coro
        return func

    return decorator  # type: ignore
