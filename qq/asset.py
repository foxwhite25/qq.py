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

import io
import os
from typing import Any, Literal, Optional, TYPE_CHECKING, Tuple, Union

import yarl
from typing_extensions import Self

from . import utils
from .error import QQException

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
        """|coro|
        获得这个素材的 :class:`bytes` 内容。

        Raises
        ------
        QQException
            没有内部连接状态。
        HTTPException
            下载素材失败。
        NotFound
            素材已删除。
        Returns
        -------
        :class:`bytes`
            素材的内容。
        """

        if self._state is None:
            raise QQException('Invalid state (no ConnectionState provided)')

        return await self._state.http.get_from_cdn(self.url)

    async def save(self, fp: Union[str, bytes, os.PathLike, io.BufferedIOBase], *, seek_begin: bool = True) -> int:
        """|coro|
        将此素材保存到类似文件的对象中。

        Parameters
        ----------
        fp: Union[:class:`io.BufferedIOBase`, :class:`os.PathLike`]
            将此附件保存到的类文件对象或要使用的文件名。
            如果传递了文件名，则会使用该文件名创建一个文件并改为使用该文件。
        seek_begin: :class:`bool`
            保存成功后是否查找文件开头。

        Raises
        ------
        QQException
            没有内部连接状态。
        HTTPException
            下载素材失败。
        NotFound
            素材已删除。

        Returns
        --------
        :class:`int`
            写入的字节数。
        """

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
    """代表 QQ 上的素材。

    .. container:: operations

        .. describe:: str(x)

            返回素材的 URL。

        .. describe:: len(x)

            返回素材 URL 的长度。

        .. describe:: x == y

            检查素材是否等于另一个素材。

        .. describe:: x != y

            检查素材是否不等于另一个素材。

        .. describe:: hash(x)

            返回素材的哈希值。
    """

    __slots__: Tuple[str, ...] = (
        '_state',
        '_url',
        '_key',
    )

    def __init__(self, state, *, url: str, key: str, animated: bool = False):
        self._state = state
        self._url = url
        self._key = key
        self._animated = animated

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
        return f'<Asset url={self._url!r}>'

    def __eq__(self, other):
        return isinstance(other, Asset) and self._url == other._url

    def __hash__(self):
        return hash(self._url)

    @property
    def url(self) -> str:
        """:class:`str`: 返回素材的底层 URL。"""
        return self._url

    @property
    def key(self) -> str:
        """:class:`str`: 返回素材的识别键。"""
        return self._key

    def is_animated(self) -> bool:
        """:class:`bool`: Returns whether the asset is animated."""
        return self._animated

    def replace(
            self,
            *,
            size: int = MISSING,
            format: ValidAssetFormatTypes = MISSING,
            static_format: ValidStaticFormatTypes = MISSING,
    ) -> Self:
        """Returns a new asset with the passed components replaced.

        Parameters
        -----------
        size: :class:`int`
            The new size of the asset.
        format: :class:`str`
            The new format to change it to. Must be either
            'webp', 'jpeg', 'jpg', 'png', or 'gif' if it's animated.
        static_format: :class:`str`
            The new format to change it to if the asset isn't animated.
            Must be either 'webp', 'jpeg', 'jpg', or 'png'.

        Raises
        -------
        ValueError
            An invalid size or format was passed.

        Returns
        --------
        :class:`Asset`
            The newly updated asset.
        """
        url = yarl.URL(self._url)
        path, _ = os.path.splitext(url.path)

        if format is not MISSING:
            if self._animated:
                if format not in VALID_ASSET_FORMATS:
                    raise ValueError(f'format must be one of {VALID_ASSET_FORMATS}')
            else:
                if format not in VALID_STATIC_FORMATS:
                    raise ValueError(f'format must be one of {VALID_STATIC_FORMATS}')
            url = url.with_path(f'{path}.{format}')

        if static_format is not MISSING and not self._animated:
            if static_format not in VALID_STATIC_FORMATS:
                raise ValueError(f'static_format must be one of {VALID_STATIC_FORMATS}')
            url = url.with_path(f'{path}.{static_format}')

        if size is not MISSING:
            if not utils.valid_icon_size(size):
                raise ValueError('size must be a power of 2 between 16 and 4096')
            url = url.with_query(size=size)
        else:
            url = url.with_query(url.raw_query_string)

        url = str(url)
        return Asset(state=self._state, url=url, key=self._key, animated=self._animated)

    def with_size(self, size: int, /) -> Self:
        """Returns a new asset with the specified size.

        Parameters
        ------------
        size: :class:`int`
            The new size of the asset.

        Raises
        -------
        ValueError
            The asset had an invalid size.

        Returns
        --------
        :class:`Asset`
            The new updated asset.
        """
        if not utils.valid_icon_size(size):
            raise ValueError('size must be a power of 2 between 16 and 4096')

        url = str(yarl.URL(self._url).with_query(size=size))
        return Asset(state=self._state, url=url, key=self._key, animated=self._animated)

    def with_format(self, format: ValidAssetFormatTypes, /) -> Self:
        """Returns a new asset with the specified format.

        Parameters
        ------------
        format: :class:`str`
            The new format of the asset.

        Raises
        -------
        ValueError
            The asset had an invalid format.

        Returns
        --------
        :class:`Asset`
            The new updated asset.
        """

        if self._animated:
            if format not in VALID_ASSET_FORMATS:
                raise ValueError(f'format must be one of {VALID_ASSET_FORMATS}')
        else:
            if format not in VALID_STATIC_FORMATS:
                raise ValueError(f'format must be one of {VALID_STATIC_FORMATS}')

        url = yarl.URL(self._url)
        path, _ = os.path.splitext(url.path)
        url = str(url.with_path(f'{path}.{format}').with_query(url.raw_query_string))
        return Asset(state=self._state, url=url, key=self._key, animated=self._animated)

    def with_static_format(self, format: ValidStaticFormatTypes, /) -> Self:
        """Returns a new asset with the specified static format.
        This only changes the format if the underlying asset is
        not animated. Otherwise, the asset is not changed.

        Parameters
        ------------
        format: :class:`str`
            The new static format of the asset.

        Raises
        -------
        ValueError
            The asset had an invalid format.

        Returns
        --------
        :class:`Asset`
            The new updated asset.
        """

        if self._animated:
            return self
        return self.with_format(format)
