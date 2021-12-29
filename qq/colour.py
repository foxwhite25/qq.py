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

import colorsys
import random

from typing import (
    Any,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

__all__ = (
    'Colour',
    'Color',
)

CT = TypeVar('CT', bound='Colour')


class Colour:
    """
    代表 QQ 颜色。这个类类似于（红、绿、蓝）:class:`tuple` 。
    这个有一个别名叫做 Color。

    .. container:: operations

        .. describe:: x == y

             检查两种颜色是否相等。

        .. describe:: x != y

             检查两种颜色是否不相等。

        .. describe:: hash(x)

             返回颜色的哈希值。

        .. describe:: str(x)

             返回颜色的十六进制格式。

        .. describe:: int(x)

             返回原始颜色值。

    Attributes
    ------------
    value: :class:`int`
        原始整数颜色值。
    """

    __slots__ = ('value',)

    def __init__(self, value: int):
        if not isinstance(value, int):
            raise TypeError(f'Expected int parameter, received {value.__class__.__name__} instead.')

        self.value: int = value

    def _get_byte(self, byte: int) -> int:
        return (self.value >> (8 * byte)) & 0xff

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Colour) and self.value == other.value

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return f'#{self.value:0>6x}'

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return f'<Colour value={self.value}>'

    def __hash__(self) -> int:
        return hash(self.value)

    @property
    def r(self) -> int:
        """:class:`int`: 返回颜色的红色部分。"""
        return self._get_byte(2)

    @property
    def g(self) -> int:
        """:class:`int`: 返回颜色的绿色部分。"""
        return self._get_byte(1)

    @property
    def b(self) -> int:
        """:class:`int`: 返回颜色的蓝色部分。"""
        return self._get_byte(0)

    def to_rgb(self) -> Tuple[int, int, int]:
        """Tuple[:class:`int`, :class:`int`, :class:`int`]: 返回表示颜色的 (r, g, b) 元组。"""
        return (self.r, self.g, self.b)

    @classmethod
    def from_rgb(cls: Type[CT], r: int, g: int, b: int) -> CT:
        """Constructs a :class:`Colour` 来自 RGB 元组。"""
        return cls((r << 16) + (g << 8) + b)

    @classmethod
    def from_hsv(cls: Type[CT], h: float, s: float, v: float) -> CT:
        """Constructs a :class:`Colour` 来自 HSV 元组。"""
        rgb = colorsys.hsv_to_rgb(h, s, v)
        return cls.from_rgb(*(int(x * 255) for x in rgb))

    @classmethod
    def default(cls: Type[CT]) -> CT:
        """一个工厂方法，它返回一个 :class:`Colour` 的值为 ``0`` 。"""
        return cls(0)

    @classmethod
    def random(cls: Type[CT], *, seed: Optional[Union[int, str, float, bytes, bytearray]] = None) -> CT:
        """返回带有随机色调的 :class:`Colour` 的工厂方法。

        .. note::

            随机算法的工作原理是选择具有随机色调但饱和度和值最大化的颜色。

        Parameters
        ------------
        seed: Optional[Union[:class:`int`, :class:`str`, :class:`float`, :class:`bytes`, :class:`bytearray`]]
            用于初始化随机数生成器的种子。如果传递 ``None``，则使用默认随机数生成器。

        """
        rand = random if seed is None else random.Random(seed)
        return cls.from_hsv(rand.random(), 1, 1)

    @classmethod
    def teal(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x1abc9c`` 的 :class:`Colour`  。"""
        return cls(0x1abc9c)

    @classmethod
    def dark_teal(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x11806a`` 的 :class:`Colour`  。"""
        return cls(0x11806a)

    @classmethod
    def brand_green(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x57F287`` 的 :class:`Colour`  。"""
        return cls(0x57F287)

    @classmethod
    def green(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x2ecc71`` 的 :class:`Colour`  。"""
        return cls(0x2ecc71)

    @classmethod
    def dark_green(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x1f8b4c`` 的 :class:`Colour`  。"""
        return cls(0x1f8b4c)

    @classmethod
    def blue(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x3498db`` 的 :class:`Colour`  。"""
        return cls(0x3498db)

    @classmethod
    def dark_blue(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x206694`` 的 :class:`Colour`  。"""
        return cls(0x206694)

    @classmethod
    def purple(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x9b59b6`` 的 :class:`Colour`  。"""
        return cls(0x9b59b6)

    @classmethod
    def dark_purple(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x71368a`` 的 :class:`Colour`  。"""
        return cls(0x71368a)

    @classmethod
    def magenta(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xe91e63`` 的 :class:`Colour`  。"""
        return cls(0xe91e63)

    @classmethod
    def dark_magenta(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xad1457`` 的 :class:`Colour`  。"""
        return cls(0xad1457)

    @classmethod
    def gold(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xf1c40f`` 的 :class:`Colour`  。"""
        return cls(0xf1c40f)

    @classmethod
    def dark_gold(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xc27c0e`` 的 :class:`Colour`  。"""
        return cls(0xc27c0e)

    @classmethod
    def orange(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xe67e22`` 的 :class:`Colour`  。"""
        return cls(0xe67e22)

    @classmethod
    def dark_orange(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xa84300`` 的 :class:`Colour`  。"""
        return cls(0xa84300)

    @classmethod
    def brand_red(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xED4245`` 的 :class:`Colour`  。"""
        return cls(0xED4245)

    @classmethod
    def red(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xe74c3c`` 的 :class:`Colour`  。"""
        return cls(0xe74c3c)

    @classmethod
    def dark_red(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x992d22`` 的 :class:`Colour`  。"""
        return cls(0x992d22)

    @classmethod
    def lighter_grey(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x95a5a6`` 的 :class:`Colour`  。"""
        return cls(0x95a5a6)

    lighter_gray = lighter_grey

    @classmethod
    def dark_grey(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x607d8b`` 的 :class:`Colour`  。"""
        return cls(0x607d8b)

    dark_gray = dark_grey

    @classmethod
    def light_grey(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x979c9f`` 的 :class:`Colour`  。"""
        return cls(0x979c9f)

    light_gray = light_grey

    @classmethod
    def darker_grey(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x546e7a`` 的 :class:`Colour`  。"""
        return cls(0x546e7a)

    darker_gray = darker_grey

    @classmethod
    def og_blurple(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x7289da`` 的 :class:`Colour`  。"""
        return cls(0x7289da)

    @classmethod
    def blurple(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x5865F2`` 的 :class:`Colour`  。"""
        return cls(0x5865F2)

    @classmethod
    def greyple(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x99aab5`` 的 :class:`Colour`  。"""
        return cls(0x99aab5)

    @classmethod
    def dark_theme(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0x36393F`` 的 :class:`Colour`  。"""
        return cls(0x36393F)

    @classmethod
    def fuchsia(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xEB459E`` 的 :class:`Colour`  。"""
        return cls(0xEB459E)

    @classmethod
    def yellow(cls: Type[CT]) -> CT:
        """一个工厂方法，返回一个值为 ``0xFEE75C`` 的 :class:`Colour`  。"""
        return cls(0xFEE75C)


Color = Colour
