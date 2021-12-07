from __future__ import annotations

from typing import Type, Optional, Any, TypeVar, Callable, overload, Iterator, Tuple, ClassVar, Dict

FV = TypeVar('FV', bound='flag_value')
BF = TypeVar('BF', bound='BaseFlags')


class flag_value:
    def __init__(self, func: Callable[[Any], int]):
        self.flag = func(None)
        self.__doc__ = func.__doc__

    @overload
    def __get__(self: FV, instance: None, owner: Type[BF]) -> FV:
        ...

    @overload
    def __get__(self, instance: BF, owner: Type[BF]) -> bool:
        ...

    def __get__(self, instance: Optional[BF], owner: Type[BF]) -> Any:
        if instance is None:
            return self
        return instance._has_flag(self.flag)

    def __set__(self, instance: BF, value: bool) -> None:
        instance._set_flag(self.flag, value)

    def __repr__(self):
        return f'<flag_value flag={self.flag!r}>'


class alias_flag_value(flag_value):
    pass


class BaseFlags:
    VALID_FLAGS: ClassVar[Dict[str, int]]
    DEFAULT_VALUE: ClassVar[int]

    value: int

    __slots__ = ('value',)

    def __init__(self, **kwargs: bool):
        self.value = self.DEFAULT_VALUE
        for key, value in kwargs.items():
            if key not in self.VALID_FLAGS:
                raise TypeError(f'{key!r} is not a valid flag name.')
            setattr(self, key, value)

    @classmethod
    def _from_value(cls, value):
        self = cls.__new__(cls)
        self.value = value
        return self

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.value == other.value

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} value={self.value}>'

    def __iter__(self) -> Iterator[Tuple[str, bool]]:
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, alias_flag_value):
                continue

            if isinstance(value, flag_value):
                yield name, self._has_flag(value.flag)

    def _has_flag(self, o: int) -> bool:
        return (self.value & o) == o

    def _set_flag(self, o: int, toggle: bool) -> None:
        if toggle is True:
            self.value |= o
        elif toggle is False:
            self.value &= ~o
        else:
            raise TypeError(f'Value to set for {self.__class__.__name__} must be a bool.')


def fill_with_flags(*, inverted: bool = False):
    def decorator(cls: Type[BF]):
        # fmt: off
        cls.VALID_FLAGS = {
            name: value.flag
            for name, value in cls.__dict__.items()
            if isinstance(value, flag_value)
        }
        # fmt: on

        if inverted:
            max_bits = max(cls.VALID_FLAGS.values()).bit_length()
            cls.DEFAULT_VALUE = -1 + (2 ** max_bits)
        else:
            cls.DEFAULT_VALUE = 0

        return cls

    return decorator


@fill_with_flags()
class Intents(BaseFlags):
    __slots__ = ()

    def __init__(self, **kwargs: bool):
        self.value = self.DEFAULT_VALUE
        for key, value in kwargs.items():
            if key not in self.VALID_FLAGS:
                raise TypeError(f'{key!r} is not a valid flag name.')
            setattr(self, key, value)

    @classmethod
    def all(cls: Type[Intents]) -> Intents:
        """A factory method that creates a :class:`Intents` with everything enabled."""
        bits = max(cls.VALID_FLAGS.values()).bit_length()
        value = (1 << bits) - 1
        self = cls.__new__(cls)
        self.value = value
        return self

    @classmethod
    def none(cls: Type[Intents]) -> Intents:
        """A factory method that creates a :class:`Intents` with everything disabled."""
        self = cls.__new__(cls)
        self.value = self.DEFAULT_VALUE
        return self

    @classmethod
    def default(cls: Type[Intents]) -> Intents:
        """A factory method that creates a :class:`Intents` with everything enabled
        except :attr:`presences` and :attr:`members`.
        """
        self = cls.all()
        self.audio = False
        self.direct_messages = False
        return self

    @flag_value
    def guilds(self):
        return 1 << 0

    @flag_value
    def members(self):
        return 1 << 1

    @flag_value
    def direct_messages(self):
        return 1 << 12

    @flag_value
    def audio(self):
        return 1 << 29

    @flag_value
    def at_messages(self):
        return 1 << 30
