from __future__ import annotations

import datetime
from typing import Any, Dict, Final, List, Mapping, Protocol, TYPE_CHECKING, Type, TypeVar, Union

__all__ = (
    'Embed',
)


class _EmptyEmbed:
    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return 'Embed.Empty'

    def __len__(self) -> int:
        return 0


EmptyEmbed: Final = _EmptyEmbed()


class EmbedProxy:
    def __init__(self, layer: Dict[str, Any]):
        self.__dict__.update(layer)

    def __len__(self) -> int:
        return len(self.__dict__)

    def __repr__(self) -> str:
        inner = ', '.join((f'{k}={v!r}' for k, v in self.__dict__.items() if not k.startswith('_')))
        return f'EmbedProxy({inner})'

    def __getattr__(self, attr: str) -> _EmptyEmbed:
        return EmptyEmbed


E = TypeVar('E', bound='Embed')

if TYPE_CHECKING:
    from .types.embed import Embed as EmbedData

    T = TypeVar('T')
    MaybeEmpty = Union[T, _EmptyEmbed]


    class _EmbedFooterProxy(Protocol):
        text: MaybeEmpty[str]
        icon_url: MaybeEmpty[str]


    class _EmbedFieldProxy(Protocol):
        name: MaybeEmpty[str]
        value: MaybeEmpty[str]
        inline: bool


    class _EmbedMediaProxy(Protocol):
        url: MaybeEmpty[str]
        proxy_url: MaybeEmpty[str]
        height: MaybeEmpty[int]
        width: MaybeEmpty[int]


    class _EmbedVideoProxy(Protocol):
        url: MaybeEmpty[str]
        height: MaybeEmpty[int]
        width: MaybeEmpty[int]


    class _EmbedProviderProxy(Protocol):
        name: MaybeEmpty[str]
        url: MaybeEmpty[str]


    class _EmbedAuthorProxy(Protocol):
        name: MaybeEmpty[str]
        url: MaybeEmpty[str]
        icon_url: MaybeEmpty[str]
        proxy_icon_url: MaybeEmpty[str]


class Embed:
    __slots__ = (
        'title',
        'timestamp',
        'fields',
        'description',
        'prompt',
        '_fields',
        '_timestamp'
    )

    Empty: Final = EmptyEmbed

    def __init__(
            self,
            *,
            title: MaybeEmpty[Any] = EmptyEmbed,
            description: MaybeEmpty[Any] = EmptyEmbed,
            prompt: MaybeEmpty[Any] = EmptyEmbed,
            timestamp: datetime.datetime = None,
    ):

        self.title = title
        self.description = description
        self.prompt = prompt

        if self.prompt is not EmptyEmbed:
            self.prompt = str(self.prompt)

        if self.title is not EmptyEmbed:
            self.title = str(self.title)

        if self.description is not EmptyEmbed:
            self.description = str(self.description)

        if timestamp:
            self.timestamp = timestamp

    @classmethod
    def from_dict(cls: Type[E], data: Mapping[str, Any]) -> E:
        # we are bypassing __init__ here since it doesn't apply here
        self: E = cls.__new__(cls)

        # fill in the basic fields

        self.title = data.get('title', EmptyEmbed)
        self.description = data.get('description', EmptyEmbed)
        self.prompt = data.get('prompt', EmptyEmbed)

        if self.title is not EmptyEmbed:
            self.title = str(self.title)

        if self.description is not EmptyEmbed:
            self.description = str(self.description)

        if self.prompt is not EmptyEmbed:
            self.prompt = str(self.prompt)
        return self

    def copy(self: E) -> E:
        """Returns a shallow copy of the embed."""
        return self.__class__.from_dict(self.to_dict())

    def __len__(self) -> int:
        total = len(self.title) + len(self.description) + len(self.prompt)
        for field in getattr(self, '_fields', []):
            total += len(field['name']) + len(field['value'])
        return total

    def __bool__(self) -> bool:
        return any(
            (
                self.title,
                self.description,
                self.fields,
                self.timestamp,
                self.prompt
            )
        )

    def insert_field_at(self: E, index: int, *, name: Any, value: Any) -> E:

        field = {
            'name': str(name),
            'value': str(value),
        }

        try:
            self._fields.insert(index, field)
        except AttributeError:
            self._fields = [field]

        return self

    def clear_fields(self) -> None:
        try:
            self._fields.clear()
        except AttributeError:
            self._fields = []

    def remove_field(self, index: int) -> None:
        try:
            del self._fields[index]
        except (AttributeError, IndexError):
            pass

    def set_field_at(self: E, index: int, *, name: Any, value: Any) -> E:
        try:
            field = self._fields[index]
        except (TypeError, IndexError, AttributeError):
            raise IndexError('field index out of range')

        field['name'] = str(name)
        field['value'] = str(value)
        return self

    def to_dict(self) -> EmbedData:
        """Converts this embed object into a dict."""

        # add in the raw data into the dict
        # fmt: off
        result = {
            key[1:]: getattr(self, key)
            for key in self.__slots__
            if key[0] == '_' and hasattr(self, key)
        }

        try:
            timestamp = result.pop('timestamp')
        except KeyError:
            pass
        else:
            if timestamp:
                if timestamp.tzinfo:
                    result['timestamp'] = timestamp.astimezone(tz=datetime.timezone.utc).isoformat()
                else:
                    result['timestamp'] = timestamp.replace(tzinfo=datetime.timezone.utc).isoformat()

        if self.description:
            result['description'] = self.description

        if self.title:
            result['title'] = self.title

        if self.prompt:
            result['prompt'] = self.prompt

        return result  # type: ignore
