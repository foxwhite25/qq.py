from __future__ import annotations

import base64
from typing import Optional, TYPE_CHECKING, Union

import os
import io

__all__ = (
    'File',
)


class File:
    __slots__ = ('fp', 'filename', 'spoiler', '_original_pos', '_owner', '_closer')

    if TYPE_CHECKING:
        fp: io.BufferedIOBase
        filename: Optional[str]
        spoiler: bool

    def __init__(
        self,
        fp: Union[str, bytes, os.PathLike, io.BufferedIOBase],
        filename: Optional[str] = None,
        *,
        spoiler: bool = False,
    ):
        if isinstance(fp, io.IOBase):
            if not (fp.seekable() and fp.readable()):
                raise ValueError(f'File buffer {fp!r} must be seekable and readable')
            self.fp = fp
            self._original_pos = fp.tell()
            self._owner = False
        else:
            self.fp = open(fp, 'rb')
            self._original_pos = 0
            self._owner = True

        # aiohttp only uses two methods from IOBase
        # read and close, since I want to control when the files
        # close, I need to stub it so it doesn't close unless
        # I tell it to
        self._closer = self.fp.close
        self.fp.close = lambda: None

        if filename is None:
            if isinstance(fp, str):
                _, self.filename = os.path.split(fp)
            else:
                self.filename = getattr(fp, 'name', None)
        else:
            self.filename = filename

        if spoiler and self.filename is not None and not self.filename.startswith('SPOILER_'):
            self.filename = 'SPOILER_' + self.filename

        self.spoiler = spoiler or (self.filename is not None and self.filename.startswith('SPOILER_'))

    def reset(self, *, seek: Union[int, bool] = True) -> None:
        if seek:
            self.fp.seek(self._original_pos)

    def close(self) -> None:
        self.fp.close = self._closer
        if self._owner:
            self._closer()
