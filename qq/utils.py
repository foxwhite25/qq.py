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

import array
import asyncio
import collections.abc
import datetime
import json
import re
import sys
import unicodedata
from bisect import bisect_left
from inspect import isawaitable as _isawaitable, signature as _signature
from operator import attrgetter
from typing import Any, Callable, TypeVar, overload, Optional, Iterable, List, TYPE_CHECKING, Generic, Type, Dict, \
    ForwardRef, Literal, Tuple, Union, Iterator, AsyncIterator, Sequence

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
_Iter = Union[Iterator[T], AsyncIterator[T]]
_MARKDOWN_ESCAPE_SUBREGEX = '|'.join(r'\{0}(?=([\s\S]*((?<!\{0})\{0})))'.format(c) for c in ('*', '`', '_', '~', '|'))
_MARKDOWN_ESCAPE_COMMON = r'^>(?:>>)?\s|\[.+\]\(.+\)'
_MARKDOWN_ESCAPE_REGEX = re.compile(fr'(?P<markdown>{_MARKDOWN_ESCAPE_SUBREGEX}|{_MARKDOWN_ESCAPE_COMMON})',
                                    re.MULTILINE)
_URL_REGEX = r'(?P<url><[^: >]+:\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,:;\"\'\]\s])'
_MARKDOWN_STOCK_REGEX = fr'(?P<markdown>[_\\~|\*`]|{_MARKDOWN_ESCAPE_COMMON})'

__all__ = (
    'find',
    'get',
    'sleep_until',
    'utcnow',
    'remove_markdown',
    'escape_markdown',
    'escape_mentions',
    'as_chunks',
    'format_dt',
)

_IS_ASCII = re.compile(r'^[\x00-\x7f]+$')


def _string_width(string: str, *, _IS_ASCII=_IS_ASCII) -> int:
    """Returns string's width."""
    match = _IS_ASCII.match(string)
    if match:
        return match.endpos

    UNICODE_WIDE_CHAR_TYPE = 'WFA'
    func = unicodedata.east_asian_width
    return sum(2 if func(char) in UNICODE_WIDE_CHAR_TYPE else 1 for char in string)


def utcnow() -> datetime.datetime:
    """一个辅助函数，用于返回表示当前时间的 UTC datetime。
    这应该比 :meth:`datetime.datetime.utcnow` 更可取，因为与标准库中的原始日期时间相比，它是一个 aware 的 datetime。

    Returns
    --------
    :class:`datetime.datetime`
        UTC 中的当前 datetime datetime。
    """
    return datetime.datetime.now(datetime.timezone.utc)


def _chunk(iterator: Iterator[T], max_size: int) -> Iterator[List[T]]:
    ret = []
    n = 0
    for item in iterator:
        ret.append(item)
        n += 1
        if n == max_size:
            yield ret
            ret = []
            n = 0
    if ret:
        yield ret


async def _achunk(iterator: AsyncIterator[T], max_size: int) -> AsyncIterator[List[T]]:
    ret = []
    n = 0
    async for item in iterator:
        ret.append(item)
        n += 1
        if n == max_size:
            yield ret
            ret = []
            n = 0
    if ret:
        yield ret


@overload
def as_chunks(iterator: Iterator[T], max_size: int) -> Iterator[List[T]]:
    ...


@overload
def as_chunks(iterator: AsyncIterator[T], max_size: int) -> AsyncIterator[List[T]]:
    ...


def as_chunks(iterator: _Iter[T], max_size: int) -> _Iter[List[T]]:
    """将迭代器收集到给定大小的块中的辅助函数。

    Parameters
    ----------
    iterator: Union[:class:`collections.abc.Iterator`, :class:`collections.abc.AsyncIterator`]
        块的迭代器，可以是同步的或异步的。
    max_size: :class:`int`
        最大块大小。


    .. warning::

        收集的最后一个块可能没有 ``max_size`` 那么大。

    Returns
    --------
    Union[:class:`Iterator`, :class:`AsyncIterator`]
        一个新的迭代器，它产生给定大小的块。
    """

    if max_size <= 0:
        raise ValueError('Chunk sizes must be greater than 0.')

    if isinstance(iterator, AsyncIterator):
        return _achunk(iterator, max_size)
    return _chunk(iterator, max_size)


PY_310 = sys.version_info >= (3, 10)
TimestampStyle = Literal['f', 'F', 'd', 'D', 't', 'T', 'R']


def format_dt(dt: datetime.datetime, /, style: Optional[TimestampStyle] = None) -> str:
    """用于格式化 datetime.以在 QQ 中展示的辅助函数。

    +------+----------------------------+------------+
    | 样式 | 示例输出                   | 描述       |
    +------+----------------------------+------------+
    | t    | 22:57                      | 短时间     |
    +------+----------------------------+------------+
    | T    | 22:57:58                   | 长时间     |
    +------+----------------------------+------------+
    | d    | 17/05/2016                 | 短日期     |
    +------+----------------------------+------------+
    | D    | 17 May 2016                | 长日期     |
    +------+----------------------------+------------+
    | f    | 17 May 2016 22:57          | 短日期时间 |
    +------+----------------------------+------------+
    | F    | Tuesday, 17 May 2016 22:57 | 长日期时间 |
    +------+----------------------------+------------+
    | R    | 5 years ago                | 相对时间   |
    +------+----------------------------+------------+

    请注意，确切的输出取决于客户端中用户的区域设置。显示的示例输出使用 ``en-GB`` 语言环境。

    Parameters
    -----------
    dt: :class:`datetime.datetime`
        要格式化的 datetime 。
    style: :class:`str`
        格式化日期时间的样式。

    Returns
    --------
    :class:`str`
        格式化的字符串。
    """
    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'


def compute_timedelta(dt: datetime.datetime):
    if dt.tzinfo is None:
        dt = dt.astimezone()
    now = datetime.datetime.now(datetime.timezone.utc)
    return max((dt - now).total_seconds(), 0)


async def sleep_until(when: datetime.datetime, result: Optional[T] = None) -> Optional[T]:
    """|coro|
    睡眠到指定时间。
    如果提供的时间在过去，则此函数将立即返回。

    Parameters
    -----------
    when: :class:`datetime.datetime`
        休眠到的时间戳。如果日期时间是 native 的，那么它被假定为本地时间。
    result: Any
        如果提供，则在协程完成时返回给调用者。
    """
    delta = compute_timedelta(when)
    return await asyncio.sleep(delta, result)


def remove_markdown(text: str, *, ignore_links: bool = True) -> str:
    """删除 Markdown 字符的辅助函数。

    .. note::
    
            此功能不会解析 Markdown ，可能会从原文中删除含义。 例如，
            如果输入包含 ``10 * 5`` ，那么它将被转换为 ``10 5`` 。

    Parameters
    -----------
    text: :class:`str`
        要从中删除Markdown的文本。
    ignore_links: :class:`bool`
        删除 Markdown 时是否留下链接。 例如，如果文本中的 URL 包含诸如 ``_`` 之类的字符，则它将单独保留。默认为 ``True`` 。

    Returns
    --------
    :class:`str`
        删除了 Markdown 特殊字符的文本。
    """

    def replacement(match):
        groupdict = match.groupdict()
        return groupdict.get('url', '')

    regex = _MARKDOWN_STOCK_REGEX
    if ignore_links:
        regex = f'(?:{_URL_REGEX}|{regex})'
    return re.sub(regex, replacement, text, 0, re.MULTILINE)


def escape_markdown(text: str, *, as_needed: bool = False, ignore_links: bool = True) -> str:
    r"""转义 Markdown 的辅助函数。

    Parameters
    -----------
    text: :class:`str`
        转义 markdown 的文本。
    as_needed: :class:`bool`
        是否根据需要转义Markdown字符。
        这意味着如果没有必要，它不会转义无关的字符，例如 ``hello`` 转义为 ``\\hello`` 而不是 ``\\hello\\`` 。
        但是请注意，这可能会让你面临一些奇怪的语法滥用。默认为 ``False`` 。

    ignore_links: :class:`bool`
        转义 markdown 时是否留下链接。例如，如果文本中的 URL 包含诸如 ``_`` 之类的字符，则它将单独保留。 ``as_needed`` 不支持此选项。
        默认为 ``True`` 。

    Returns
    --------
    :class:`str`
        带有 Markdown 特殊字符的文本用斜杠转义。
    """

    if not as_needed:

        def replacement(match):
            groupdict = match.groupdict()
            is_url = groupdict.get('url')
            if is_url:
                return is_url
            return '\\' + groupdict['markdown']

        regex = _MARKDOWN_STOCK_REGEX
        if ignore_links:
            regex = f'(?:{_URL_REGEX}|{regex})'
        return re.sub(regex, replacement, text, 0, re.MULTILINE)
    else:
        text = re.sub(r'\\', r'\\\\', text)
        return _MARKDOWN_ESCAPE_REGEX.sub(r'\\\1', text)


class _cached_property:
    def __init__(self, function):
        self.function = function
        self.__doc__ = getattr(function, '__doc__')

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = self.function(instance)
        setattr(instance, self.function.__name__, value)

        return value


if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec('P')

else:
    cached_property = _cached_property

try:
    import orjson
except ModuleNotFoundError:
    HAS_ORJSON = False
else:
    HAS_ORJSON = True

if HAS_ORJSON:

    def _to_json(obj: Any) -> str:  # type: ignore
        return orjson.dumps(obj).decode('utf-8')


    _from_json = orjson.loads  # type: ignore

else:

    def _to_json(obj: Any) -> str:
        return json.dumps(obj, separators=(',', ':'), ensure_ascii=True)


    _from_json = json.loads


class _MissingSentinel:
    def __eq__(self, other):
        return False

    def __bool__(self):
        return False

    def __repr__(self):
        return '...'


MISSING: Any = _MissingSentinel()


async def maybe_coroutine(f, *args, **kwargs):
    value = f(*args, **kwargs)
    if _isawaitable(value):
        return await value
    else:
        return value


def copy_doc(original: Callable) -> Callable[[T], T]:
    def decorator(overriden: T) -> T:
        overriden.__doc__ = original.__doc__
        overriden.__signature__ = _signature(original)  # type: ignore
        return overriden

    return decorator


@overload
def parse_time(timestamp: None) -> None:
    ...


@overload
def parse_time(timestamp: str) -> datetime.datetime:
    ...


@overload
def parse_time(timestamp: Optional[str]) -> Optional[datetime.datetime]:
    ...


def parse_time(timestamp: Optional[str]) -> Optional[datetime.datetime]:
    if timestamp:
        if timestamp.isnumeric():
            return datetime.datetime.fromtimestamp(int(timestamp))
        return datetime.datetime.fromisoformat(timestamp)
    return None


def _unique(iterable: Iterable[T]) -> List[T]:
    return [x for x in dict.fromkeys(iterable)]


class SnowflakeList(array.array):
    __slots__ = ()

    if TYPE_CHECKING:
        def __init__(self, data: Iterable[int], *, is_sorted: bool = False):
            ...

    def __new__(cls, data: Iterable[int], *, is_sorted: bool = False):
        return array.array.__new__(cls, 'Q', data if is_sorted else sorted(data))  # type: ignore

    def add(self, element: int) -> None:
        i = bisect_left(self, element)
        self.insert(i, element)

    def get(self, element: int) -> Optional[int]:
        i = bisect_left(self, element)
        return self[i] if i != len(self) and self[i] == element else None

    def has(self, element: int) -> bool:
        i = bisect_left(self, element)
        return i != len(self) and self[i] == element


class CachedSlotProperty(Generic[T, T_co]):
    def __init__(self, name: str, function: Callable[[T], T_co]) -> None:
        self.name = name
        self.function = function
        self.__doc__ = getattr(function, '__doc__')

    @overload
    def __get__(self, instance: None, owner: Type[T]):
        ...

    @overload
    def __get__(self, instance: T, owner: Type[T]) -> T_co:
        ...

    def __get__(self, instance: Optional[T], owner: Type[T]) -> Any:
        if instance is None:
            return self

        try:
            return getattr(instance, self.name)
        except AttributeError:
            value = self.function(instance)
            setattr(instance, self.name, value)
            return value


def cached_slot_property(name: str) -> Callable[[Callable[[T], T_co]], CachedSlotProperty[T, T_co]]:
    def decorator(func: Callable[[T], T_co]) -> CachedSlotProperty[T, T_co]:
        return CachedSlotProperty(name, func)

    return decorator


def escape_mentions(text: str) -> str:
    """一个帮助函数，可以转义所有成员，身份组和用户提及。

    .. note::

        这不包括频道提及。

    .. note::

        要对消息中的提及内容进行更精细的控制，请参阅 :class:`~qq.AllowedMentions` 类。

    Parameters
    -----------
    text: :class:`str`
        要转义的文本。

    Returns
    --------
    :class:`str`
        删除了提及的文本。
    """

    return re.sub(r'@(所有成员|[!&]?[0-9]{17,20})', '@\u200b\\1', text)


def find(predicate: Callable[[T], Any], seq: Iterable[T]) -> Optional[T]:
    """返回在满足 predicate 的序列中找到的第一个元素的帮助器。例如： ::

        member = qq.utils.find(lambda m: m.name == 'Foo', channel.guild.members)

    会找到第一个名字是 ``Mighty`` 的  :class:`~qq.Member` 并返回它。
    如果未找到条目，则返回 ``None`` 。
    这与 :func:`py:filter` 不同，因为它在找到有效条目时停止。

    Parameters
    -----------
    predicate
        返回类似布尔值的结果的函数。
    seq: :class:`collections.abc.Iterable`
        要搜索的可迭代对象。
    """

    for element in seq:
        if predicate(element):
            return element
    return None


def get(iterable: Iterable[T], **attrs: Any) -> Optional[T]:
    r"""一个帮助器，它返回可迭代对象中满足 ``attrs`` 中传递的所有特征的第一个元素。这是 :func:`~qq.utils.find` 的替代方案。
    指定多个属性时，将使用逻辑 AND 而不是逻辑 OR 检查它们。
    这意味着他们必须满足传入的每个属性，而不是其中之一。
    要进行嵌套属性搜索（即通过 ``x.y`` 搜索），然后传入 ``x__y`` 作为关键字参数。
    如果没有找到与传递的属性匹配的属性，则返回 ``None`` 。

    Examples
    ---------

    基本用法:

    .. code-block:: python3

        member = qq.utils.get(message.guild.members, name='Foo')

    多属性匹配:

    .. code-block:: python3

        member = qq.utils.get(message.guild.members, name='Foo', bot=False)

    嵌套属性匹配：

    .. code-block:: python3

        member = qq.utils.get(message.guild.members, avatar__url='xxx', name='Foo')

    Parameters
    -----------
    iterable
        一个可迭代的搜索对象。
    \*\*attrs
        表示要搜索的属性的关键字参数。
    """

    _all = all
    attrget = attrgetter

    # Special case the single element call
    if len(attrs) == 1:
        k, v = attrs.popitem()
        pred = attrget(k.replace('__', '.'))
        for elem in iterable:
            if pred(elem) == v:
                return elem
        return None

    converted = [(attrget(attr.replace('__', '.')), value) for attr, value in attrs.items()]

    for elem in iterable:
        if _all(pred(elem) == value for pred, value in converted):
            return elem
    return None


async def sane_wait_for(futures, *, timeout):
    ensured = [asyncio.ensure_future(fut) for fut in futures]
    done, pending = await asyncio.wait(ensured, timeout=timeout, return_when=asyncio.ALL_COMPLETED)

    if len(pending) != 0:
        raise asyncio.TimeoutError()

    return done


def compute_timedelta(dt: datetime.datetime):
    if dt.tzinfo is None:
        dt = dt.astimezone()
    now = datetime.datetime.now(datetime.timezone.utc)
    return max((dt - now).total_seconds(), 0)


PY_310 = sys.version_info >= (3, 10)


def flatten_literal_params(parameters: Iterable[Any]) -> Tuple[Any, ...]:
    params = []
    literal_cls = type(Literal[0])
    for p in parameters:
        if isinstance(p, literal_cls):
            params.extend(p.__args__)
        else:
            params.append(p)
    return tuple(params)


def normalise_optional_params(parameters: Iterable[Any]) -> Tuple[Any, ...]:
    none_cls = type(None)
    return tuple(p for p in parameters if p is not none_cls) + (none_cls,)


def evaluate_annotation(
        tp: Any,
        globals: Dict[str, Any],
        locals: Dict[str, Any],
        cache: Dict[str, Any],
        *,
        implicit_str: bool = True,
):
    if isinstance(tp, ForwardRef):
        tp = tp.__forward_arg__
        # ForwardRefs always evaluate their internals
        implicit_str = True

    if implicit_str and isinstance(tp, str):
        if tp in cache:
            return cache[tp]
        evaluated = eval(tp, globals, locals)
        cache[tp] = evaluated
        return evaluate_annotation(evaluated, globals, locals, cache)

    if hasattr(tp, '__args__'):
        implicit_str = True
        is_literal = False
        args = tp.__args__
        if not hasattr(tp, '__origin__'):
            if PY_310 and tp.__class__ is types.UnionType:  # type: ignore
                converted = Union[args]  # type: ignore
                return evaluate_annotation(converted, globals, locals, cache)

            return tp
        if tp.__origin__ is Union:
            try:
                if args.index(type(None)) != len(args) - 1:
                    args = normalise_optional_params(tp.__args__)
            except ValueError:
                pass
        if tp.__origin__ is Literal:
            if not PY_310:
                args = flatten_literal_params(tp.__args__)
            implicit_str = False
            is_literal = True

        evaluated_args = tuple(
            evaluate_annotation(arg, globals, locals, cache, implicit_str=implicit_str) for arg in args)

        if is_literal and not all(isinstance(x, (str, int, bool, type(None))) for x in evaluated_args):
            raise TypeError('Literal arguments must be of type str, int, bool, or NoneType.')

        if evaluated_args == args:
            return tp

        try:
            return tp.copy_with(evaluated_args)
        except AttributeError:
            return tp.__origin__[evaluated_args]

    return tp


def resolve_annotation(
        annotation: Any,
        globalns: Dict[str, Any],
        localns: Optional[Dict[str, Any]],
        cache: Optional[Dict[str, Any]],
) -> Any:
    if annotation is None:
        return type(None)
    if isinstance(annotation, str):
        annotation = ForwardRef(annotation)

    locals = globalns if localns is None else localns
    if cache is None:
        cache = {}
    return evaluate_annotation(annotation, globalns, locals, cache)


async def async_all(gen, *, check=_isawaitable):
    for elem in gen:
        if check(elem):
            elem = await elem
        if not elem:
            return False
    return True


class SequenceProxy(Generic[T_co], collections.abc.Sequence):
    """序列的只读代理。"""

    def __init__(self, proxied: Sequence[T_co]):
        self.__proxied = proxied

    def __getitem__(self, idx: int) -> T_co:
        return self.__proxied[idx]

    def __len__(self) -> int:
        return len(self.__proxied)

    def __contains__(self, item: Any) -> bool:
        return item in self.__proxied

    def __iter__(self) -> Iterator[T_co]:
        return iter(self.__proxied)

    def __reversed__(self) -> Iterator[T_co]:
        return reversed(self.__proxied)

    def index(self, value: Any, *args, **kwargs) -> int:
        return self.__proxied.index(value, *args, **kwargs)

    def count(self, value: Any) -> int:
        return self.__proxied.count(value)


def valid_icon_size(size: int) -> bool:
    """Icons must be power of 2 within [16, 4096]."""
    return not size & (size - 1) and 4096 >= size >= 16
