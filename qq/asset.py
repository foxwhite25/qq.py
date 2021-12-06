from __future__ import annotations

import io
import os
from typing import Any, Literal, Optional, TYPE_CHECKING, Tuple, Union
from .error import QQException
from . import utils

__all__ = (
    'Asset',
)

if TYPE_CHECKING:
    ValidStaticFormatTypes = Literal['webp', 'jpeg', 'jpg', 'png']
    ValidAssetFormatTypes = Literal['webp', 'jpeg', 'jpg', 'png', 'gif']

VALID_STATIC_FORMATS = frozenset({"jpeg", "jpg", "webp", "png"})
VALID_ASSET_FORMATS = VALID_STATIC_FORMATS | {"gif"}

MISSING = utils.MISSING


class AssetMixin:
    url: str
    _state: Optional[Any]

    async def read(self) -> bytes:
        if self._state is None:
            raise QQException('Invalid state (no ConnectionState provided)')

        return await self._state.http.get_from_cdn(self.url)

    async def save(self, fp: Union[str, bytes, os.PathLike, io.BufferedIOBase], *, seek_begin: bool = True) -> int:

        data = await self.read()
        if isinstance(fp, io.BufferedIOBase):
            written = fp.write(data)
            if seek_begin:
                fp.seek(0)
            return written
        else:
            with open(fp, 'wb') as f:
                return f.write(data)


class Asset(AssetMixin):

    __slots__: Tuple[str, ...] = (
        '_state',
        '_url',
        '_key',
    )

    def __init__(self, state, *, url: str, key: str, animated: bool = False):
        self._state = state
        self._url = url
        self._key = key

    @classmethod
    def _from_avatar(cls, state, avatar: str) -> Asset:
        return cls(
            state,
            url=avatar,
            key=avatar,
        )

    @classmethod
    def _from_guild_icon(cls, state, avatar: str) -> Asset:
        return cls(
            state,
            url=avatar,
            key=avatar,
        )

    def __str__(self) -> str:
        return self._url

    def __len__(self) -> int:
        return len(self._url)

    def __repr__(self):
        shorten = self._url.replace(self.BASE, '')
        return f'<Asset url={shorten!r}>'

    def __eq__(self, other):
        return isinstance(other, Asset) and self._url == other._url

    def __hash__(self):
        return hash(self._url)

    @property
    def url(self) -> str:
        """:class:`str`: Returns the underlying URL of the asset."""
        return self._url

    @property
    def key(self) -> str:
        """:class:`str`: Returns the identifying key of the asset."""
        return self._key