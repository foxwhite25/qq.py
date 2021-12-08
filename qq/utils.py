import array
import asyncio
import datetime
import json
import re
import sys
from bisect import bisect_left
from operator import attrgetter
from typing import Any, Callable, TypeVar, overload, Optional, Iterable, List, TYPE_CHECKING, Generic, Type, Dict, \
    ForwardRef, Literal, Tuple, Union
from inspect import isawaitable as _isawaitable, signature as _signature

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
_MARKDOWN_ESCAPE_SUBREGEX = '|'.join(r'\{0}(?=([\s\S]*((?<!\{0})\{0})))'.format(c) for c in ('*', '`', '_', '~', '|'))
_MARKDOWN_ESCAPE_COMMON = r'^>(?:>>)?\s|\[.+\]\(.+\)'
_MARKDOWN_ESCAPE_REGEX = re.compile(fr'(?P<markdown>{_MARKDOWN_ESCAPE_SUBREGEX}|{_MARKDOWN_ESCAPE_COMMON})',
                                    re.MULTILINE)
_URL_REGEX = r'(?P<url><[^: >]+:\/[^ >]+>|(?:https?|steam):\/\/[^\s<]+[^<.,:;\"\'\]\s])'
_MARKDOWN_STOCK_REGEX = fr'(?P<markdown>[_\\~|\*`]|{_MARKDOWN_ESCAPE_COMMON})'


def remove_markdown(text: str, *, ignore_links: bool = True) -> str:
    def replacement(match):
        groupdict = match.groupdict()
        return groupdict.get('url', '')

    regex = _MARKDOWN_STOCK_REGEX
    if ignore_links:
        regex = f'(?:{_URL_REGEX}|{regex})'
    return re.sub(regex, replacement, text, 0, re.MULTILINE)


def escape_markdown(text: str, *, as_needed: bool = False, ignore_links: bool = True) -> str:
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
    from functools import cached_property as cached_property
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
    return re.sub(r'@(everyone|here|[!&]?[0-9]{17,20})', '@\u200b\\1', text)


def find(predicate: Callable[[T], Any], seq: Iterable[T]) -> Optional[T]:
    for element in seq:
        if predicate(element):
            return element
    return None


def get(iterable: Iterable[T], **attrs: Any) -> Optional[T]:
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
