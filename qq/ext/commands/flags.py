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
import sys
from dataclasses import dataclass, field
from typing import (
    Dict,
    Iterator,
    Literal,
    Optional,
    Pattern,
    Set,
    TYPE_CHECKING,
    Tuple,
    List,
    Any,
    Type,
    TypeVar,
    Union,
)

from qq.utils import resolve_annotation, maybe_coroutine, MISSING
from .converter import run_converters
from .errors import (
    BadFlagArgument,
    CommandError,
    MissingFlagArgument,
    TooManyFlags,
    MissingRequiredFlag,
)
from .view import StringView

__all__ = (
    'Flag',
    'flag',
    'FlagConverter',
)

if TYPE_CHECKING:
    from .context import Context


@dataclass
class Flag:
    """表示 FlagConverter 的标志参数。

    :func:`~qq.ext.commands.flag` 函数有助于创建这些标志对象，但没有必要这样做。这些不能手动构建。

    Attributes
    ------------
    name: :class:`str`
        标志的名称。
    aliases: List[:class:`str`]
        标志名称的别名。
    attribute: :class:`str`
        与此标志对应的类中的属性。
    default: Any
        标志的默认值（如果可用）。
    annotation: Any
        标志的基础评估注释。
    max_args: :class:`int`
        标志可以接受的最大参数数。负值表示无限数量的参数。
    override: :class:`bool`
        多个给定值是否覆盖先前的值。
    """

    name: str = MISSING
    aliases: List[str] = field(default_factory=list)
    attribute: str = MISSING
    annotation: Any = MISSING
    default: Any = MISSING
    max_args: int = MISSING
    override: bool = MISSING
    cast_to_dict: bool = False

    @property
    def required(self) -> bool:
        """:class:`bool`: 是否需要标志。

        必需标志没有默认值。
        """
        return self.default is MISSING


def flag(
        *,
        name: str = MISSING,
        aliases: List[str] = MISSING,
        default: Any = MISSING,
        max_args: int = MISSING,
        override: bool = MISSING,
) -> Any:
    """覆盖底层 FlagConverter 类属性的默认功能和参数。

    Parameters
    ------------
    name: :class:`str`
        标志名。如果未给出，则默认为属性名称。
    aliases: List[:class:`str`]
        标志名称的别名。如果没有给出，则不会设置别名。
    default: Any
        默认参数。这可以是一个值，也可以是一个以 :class:`Context` 作为其唯一参数的可调用对象。如果未给出，则默认为赋予属性的默认值。
    max_args: :class:`int`
        标志可以接受的最大参数数。负值表示无限数量的参数。默认值取决于给定的注释。
    override: :class:`bool`
        多个给定值是否覆盖先前的值。默认值取决于给定的注释。
    """
    return Flag(name=name, aliases=aliases, default=default, max_args=max_args, override=override)


def validate_flag_name(name: str, forbidden: Set[str]):
    if not name:
        raise ValueError('标志名称不应为空')

    for ch in name:
        if ch.isspace():
            raise ValueError(f'标志名称 {name!r} 不能有空格')
        if ch == '\\':
            raise ValueError(f'标志名称 {name!r} 不能有反斜杠')
        if ch in forbidden:
            raise ValueError(f'标志名称 {name!r} 不能包含任何 {forbidden!r}')


def get_flags(namespace: Dict[str, Any], globals: Dict[str, Any], locals: Dict[str, Any]) -> Dict[str, Flag]:
    annotations = namespace.get('__annotations__', {})
    case_insensitive = namespace['__commands_flag_case_insensitive__']
    flags: Dict[str, Flag] = {}
    cache: Dict[str, Any] = {}
    names: Set[str] = set()
    for name, annotation in annotations.items():
        flag = namespace.pop(name, MISSING)
        if isinstance(flag, Flag):
            flag.annotation = annotation
        else:
            flag = Flag(name=name, annotation=annotation, default=flag)

        flag.attribute = name
        if flag.name is MISSING:
            flag.name = name

        annotation = flag.annotation = resolve_annotation(flag.annotation, globals, locals, cache)

        if flag.default is MISSING and hasattr(annotation,
                                               '__commands_is_flag__') and annotation._can_be_constructible():
            flag.default = annotation._construct_default

        if flag.aliases is MISSING:
            flag.aliases = []

        # Add sensible defaults based off of the type annotation
        # <type> -> (max_args=1)
        # List[str] -> (max_args=-1)
        # Tuple[int, ...] -> (max_args=1)
        # Dict[K, V] -> (max_args=-1, override=True)
        # Union[str, int] -> (max_args=1)
        # Optional[str] -> (default=None, max_args=1)

        try:
            origin = annotation.__origin__
        except AttributeError:
            # A regular type hint
            if flag.max_args is MISSING:
                flag.max_args = 1
        else:
            if origin is Union:
                # typing.Union
                if flag.max_args is MISSING:
                    flag.max_args = 1
                if annotation.__args__[-1] is type(None) and flag.default is MISSING:
                    # typing.Optional
                    flag.default = None
            elif origin is tuple:
                # typing.Tuple
                # tuple parsing is e.g. `flag: peter 20`
                # for Tuple[str, int] would give you flag: ('peter', 20)
                if flag.max_args is MISSING:
                    flag.max_args = 1
            elif origin is list:
                # typing.List
                if flag.max_args is MISSING:
                    flag.max_args = -1
            elif origin is dict:
                # typing.Dict[K, V]
                # Equivalent to:
                # typing.List[typing.Tuple[K, V]]
                flag.cast_to_dict = True
                if flag.max_args is MISSING:
                    flag.max_args = -1
                if flag.override is MISSING:
                    flag.override = True
            elif origin is Literal:
                if flag.max_args is MISSING:
                    flag.max_args = 1
            else:
                raise TypeError(f'{flag.name!r} 标志不支持键入注释 {annotation!r}')

        if flag.override is MISSING:
            flag.override = False

        # Validate flag names are unique
        name = flag.name.casefold() if case_insensitive else flag.name
        if name in names:
            raise TypeError(f'{flag.name!r} 标志与之前的标志或别名冲突。')
        else:
            names.add(name)

        for alias in flag.aliases:
            # Validate alias is unique
            alias = alias.casefold() if case_insensitive else alias
            if alias in names:
                raise TypeError(f'{flag.name!r} 标志别名 {alias!r} 与之前的标志或别名冲突。')
            else:
                names.add(alias)

        flags[flag.name] = flag

    return flags


class FlagsMeta(type):
    if TYPE_CHECKING:
        __commands_is_flag__: bool
        __commands_flags__: Dict[str, Flag]
        __commands_flag_aliases__: Dict[str, str]
        __commands_flag_regex__: Pattern[str]
        __commands_flag_case_insensitive__: bool
        __commands_flag_delimiter__: str
        __commands_flag_prefix__: str

    def __new__(
            cls: Type[type],
            name: str,
            bases: Tuple[type, ...],
            attrs: Dict[str, Any],
            *,
            case_insensitive: bool = MISSING,
            delimiter: str = MISSING,
            prefix: str = MISSING,
    ):
        attrs['__commands_is_flag__'] = True

        try:
            global_ns = sys.modules[attrs['__module__']].__dict__
        except KeyError:
            global_ns = {}

        frame = inspect.currentframe()
        try:
            if frame is None:
                local_ns = {}
            else:
                if frame.f_back is None:
                    local_ns = frame.f_locals
                else:
                    local_ns = frame.f_back.f_locals
        finally:
            del frame

        flags: Dict[str, Flag] = {}
        aliases: Dict[str, str] = {}
        for base in reversed(bases):
            if base.__dict__.get('__commands_is_flag__', False):
                flags.update(base.__dict__['__commands_flags__'])
                aliases.update(base.__dict__['__commands_flag_aliases__'])
                if case_insensitive is MISSING:
                    attrs['__commands_flag_case_insensitive__'] = base.__dict__['__commands_flag_case_insensitive__']
                if delimiter is MISSING:
                    attrs['__commands_flag_delimiter__'] = base.__dict__['__commands_flag_delimiter__']
                if prefix is MISSING:
                    attrs['__commands_flag_prefix__'] = base.__dict__['__commands_flag_prefix__']

        if case_insensitive is not MISSING:
            attrs['__commands_flag_case_insensitive__'] = case_insensitive
        if delimiter is not MISSING:
            attrs['__commands_flag_delimiter__'] = delimiter
        if prefix is not MISSING:
            attrs['__commands_flag_prefix__'] = prefix

        case_insensitive = attrs.setdefault('__commands_flag_case_insensitive__', False)
        delimiter = attrs.setdefault('__commands_flag_delimiter__', ':')
        prefix = attrs.setdefault('__commands_flag_prefix__', '')

        for flag_name, flag in get_flags(attrs, global_ns, local_ns).items():
            flags[flag_name] = flag
            aliases.update({alias_name: flag_name for alias_name in flag.aliases})

        forbidden = set(delimiter).union(prefix)
        for flag_name in flags:
            validate_flag_name(flag_name, forbidden)
        for alias_name in aliases:
            validate_flag_name(alias_name, forbidden)

        regex_flags = 0
        if case_insensitive:
            flags = {key.casefold(): value for key, value in flags.items()}
            aliases = {key.casefold(): value.casefold() for key, value in aliases.items()}
            regex_flags = re.IGNORECASE

        keys = list(re.escape(k) for k in flags)
        keys.extend(re.escape(a) for a in aliases)
        keys = sorted(keys, key=lambda t: len(t), reverse=True)

        joined = '|'.join(keys)
        pattern = re.compile(f'(({re.escape(prefix)})(?P<flag>{joined}){re.escape(delimiter)})', regex_flags)
        attrs['__commands_flag_regex__'] = pattern
        attrs['__commands_flags__'] = flags
        attrs['__commands_flag_aliases__'] = aliases

        return type.__new__(cls, name, bases, attrs)


async def tuple_convert_all(ctx: Context, argument: str, flag: Flag, converter: Any) -> Tuple[Any, ...]:
    view = StringView(argument)
    results = []
    param: inspect.Parameter = ctx.current_parameter  # type: ignore
    while not view.eof:
        view.skip_ws()
        if view.eof:
            break

        word = view.get_quoted_word()
        if word is None:
            break

        try:
            converted = await run_converters(ctx, converter, word, param)
        except CommandError:
            raise
        except Exception as e:
            raise BadFlagArgument(flag) from e
        else:
            results.append(converted)

    return tuple(results)


async def tuple_convert_flag(ctx: Context, argument: str, flag: Flag, converters: Any) -> Tuple[Any, ...]:
    view = StringView(argument)
    results = []
    param: inspect.Parameter = ctx.current_parameter  # type: ignore
    for converter in converters:
        view.skip_ws()
        if view.eof:
            break

        word = view.get_quoted_word()
        if word is None:
            break

        try:
            converted = await run_converters(ctx, converter, word, param)
        except CommandError:
            raise
        except Exception as e:
            raise BadFlagArgument(flag) from e
        else:
            results.append(converted)

    if len(results) != len(converters):
        raise BadFlagArgument(flag)

    return tuple(results)


async def convert_flag(ctx, argument: str, flag: Flag, annotation: Any = None) -> Any:
    param: inspect.Parameter = ctx.current_parameter  # type: ignore
    annotation = annotation or flag.annotation
    try:
        origin = annotation.__origin__
    except AttributeError:
        pass
    else:
        if origin is tuple:
            if annotation.__args__[-1] is Ellipsis:
                return await tuple_convert_all(ctx, argument, flag, annotation.__args__[0])
            else:
                return await tuple_convert_flag(ctx, argument, flag, annotation.__args__)
        elif origin is list:
            # typing.List[x]
            annotation = annotation.__args__[0]
            return await convert_flag(ctx, argument, flag, annotation)
        elif origin is Union and annotation.__args__[-1] is type(None):
            # typing.Optional[x]
            annotation = Union[annotation.__args__[:-1]]
            return await run_converters(ctx, annotation, argument, param)
        elif origin is dict:
            # typing.Dict[K, V] -> typing.Tuple[K, V]
            return await tuple_convert_flag(ctx, argument, flag, annotation.__args__)

    try:
        return await run_converters(ctx, annotation, argument, param)
    except CommandError:
        raise
    except Exception as e:
        raise BadFlagArgument(flag) from e


F = TypeVar('F', bound='FlagConverter')


class FlagConverter(metaclass=FlagsMeta):
    """允许用户友好标志语法的转换器。

    这些标志是使用 :pep:`526` 类型注释定义的，类似于 Python 模块 :mod:`dataclasses` 。
    有关此转换器如何工作的更多信息，请查看相应的 :ref:`文档 <ext_commands_flag_converter>` 。

    .. container:: operations

        .. describe:: iter(x)

            返回 ``(flag_name, flag_value)`` 对的迭代器。
            例如，这允许将其构造为字典或对列表。请注意，未显示别名。

    Parameters
    -----------
    case_insensitive: :class:`bool`
        用于切换标志解析不区分大小写的类参数。如果为 ``True`` ，则以不区分大小写的方式解析标志。默认为 ``False`` 。
    prefix: :class:`str`
        所有标志都必须带有前缀的前缀。默认情况下没有前缀。
    delimiter: :class:`str`
        将标志的参数与标志的名称分开的分隔符。默认情况下，这是 ``:`` 。
    """

    @classmethod
    def get_flags(cls) -> Dict[str, Flag]:
        """Dict[:class:`str`, :class:`Flag`]: 标志名称到此转换器具有的标志对象的映射。"""
        return cls.__commands_flags__.copy()

    @classmethod
    def _can_be_constructible(cls) -> bool:
        return all(not flag.required for flag in cls.__commands_flags__.values())

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        for flag in self.__class__.__commands_flags__.values():
            yield (flag.name, getattr(self, flag.attribute))

    @classmethod
    async def _construct_default(cls: Type[F], ctx: Context) -> F:
        self: F = cls.__new__(cls)
        flags = cls.__commands_flags__
        for flag in flags.values():
            if callable(flag.default):
                default = await maybe_coroutine(flag.default, ctx)
                setattr(self, flag.attribute, default)
            else:
                setattr(self, flag.attribute, flag.default)
        return self

    def __repr__(self) -> str:
        pairs = ' '.join([f'{flag.attribute}={getattr(self, flag.attribute)!r}' for flag in self.get_flags().values()])
        return f'<{self.__class__.__name__} {pairs}>'

    @classmethod
    def parse_flags(cls, argument: str) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}
        flags = cls.__commands_flags__
        aliases = cls.__commands_flag_aliases__
        last_position = 0
        last_flag: Optional[Flag] = None

        case_insensitive = cls.__commands_flag_case_insensitive__
        for match in cls.__commands_flag_regex__.finditer(argument):
            begin, end = match.span(0)
            key = match.group('flag')
            if case_insensitive:
                key = key.casefold()

            if key in aliases:
                key = aliases[key]

            flag = flags.get(key)
            if last_position and last_flag is not None:
                value = argument[last_position: begin - 1].lstrip()
                if not value:
                    raise MissingFlagArgument(last_flag)

                try:
                    values = result[last_flag.name]
                except KeyError:
                    result[last_flag.name] = [value]
                else:
                    values.append(value)

            last_position = end
            last_flag = flag

        # Add the remaining string to the last available flag
        if last_position and last_flag is not None:
            value = argument[last_position:].strip()
            if not value:
                raise MissingFlagArgument(last_flag)

            try:
                values = result[last_flag.name]
            except KeyError:
                result[last_flag.name] = [value]
            else:
                values.append(value)

        # Verification of values will come at a later stage
        return result

    @classmethod
    async def convert(cls: Type[F], ctx: Context, argument: str) -> F:
        """|coro|

        实际将参数转换为标志映射的方法。

        Parameters
        ----------
        cls: Type[:class:`FlagConverter`]
            标志转换器类。
        ctx: :class:`Context`
            调用 context 。
        argument: :class:`str`
            要转换的参数。

        Raises
        --------
        FlagError
            与标志相关的解析错误。
        CommandError
            命令相关的错误。

        Returns
        --------
        :class:`FlagConverter`
            已解析所有标志的标志转换器实例。
        """
        arguments = cls.parse_flags(argument)
        flags = cls.__commands_flags__

        self: F = cls.__new__(cls)
        for name, flag in flags.items():
            try:
                values = arguments[name]
            except KeyError:
                if flag.required:
                    raise MissingRequiredFlag(flag)
                else:
                    if callable(flag.default):
                        default = await maybe_coroutine(flag.default, ctx)
                        setattr(self, flag.attribute, default)
                    else:
                        setattr(self, flag.attribute, flag.default)
                    continue

            if flag.max_args > 0 and len(values) > flag.max_args:
                if flag.override:
                    values = values[-flag.max_args:]
                else:
                    raise TooManyFlags(flag, values)

            # Special case:
            if flag.max_args == 1:
                value = await convert_flag(ctx, values[0], flag)
                setattr(self, flag.attribute, value)
                continue

            # Another special case, tuple parsing.
            # Tuple parsing is basically converting arguments within the flag
            # So, given flag: hello 20 as the input and Tuple[str, int] as the type hint
            # We would receive ('hello', 20) as the resulting value
            # This uses the same whitespace and quoting rules as regular parameters.
            values = [await convert_flag(ctx, value, flag) for value in values]

            if flag.cast_to_dict:
                values = dict(values)  # type: ignore

            setattr(self, flag.attribute, values)

        return self
