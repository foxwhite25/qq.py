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

from typing import Callable, Any, ClassVar, Dict, Iterator, Set, TYPE_CHECKING, Tuple, Type, TypeVar, Optional

from .flags import BaseFlags, flag_value, fill_with_flags, alias_flag_value

__all__ = (
    'Permissions',
    'PermissionOverwrite',
)


# A permission alias works like a regular flag but is marked
# So the PermissionOverwrite knows to work with it
class permission_alias(alias_flag_value):
    alias: str


def make_permission_alias(alias: str) -> Callable[[Callable[[Any], int]], permission_alias]:
    def decorator(func: Callable[[Any], int]) -> permission_alias:
        ret = permission_alias(func)
        ret.alias = alias
        return ret

    return decorator


P = TypeVar('P', bound='Permissions')


@fill_with_flags()
class Permissions(BaseFlags):
    """QQ 权限值。提供的属性有两种方式。你可以使用属性设置和检索单个位，就像它们是常规布尔值一样。这允许你编辑权限。

    .. container:: operations
    
        .. describe:: x == y
        
            检查两个权限是否相等。
            
        .. describe:: x != y
        
            检查两个权限是否不相等。
            
        .. describe:: x <= y
        
            检查一个权限是否是另一个权限的子集。
            
        .. describe:: x >= y
        
            检查一个权限是否是另一个权限的超集。
            
        .. describe:: x < y
        
             检查一个权限是否是另一个权限的严格子集。
             
        .. describe:: x > y
        
             检查一个权限是否是另一个权限的严格超集。
             
        .. describe:: hash(x)
        
               返回权限的哈希值。
               
        .. describe:: iter(x)
        
               返回 ``(perm, value)`` 对的迭代器。 例如，这允许将其构造为字典或对列表。请注意，未显示别名。
               
    Attributes
    -----------
    value: :class:`int`
        原始值。该值是一个 53 位整数的位数组字段，表示当前可用的权限。你应该通过属性查询权限，而不是使用此原始值。
    """

    __slots__ = ()

    def __init__(self, permissions: int = 0, **kwargs: bool):
        if not isinstance(permissions, int):
            raise TypeError(f'预期的 int 参数，而是收到 {permissions.__class__.__name__}。')

        self.value = permissions
        for key, value in kwargs.items():
            if key not in self.VALID_FLAGS:
                raise TypeError(f'{key!r} 不是有效的权限名称。')
            setattr(self, key, value)

    def is_subset(self, other: Permissions) -> bool:
        """如果 self 与 other 具有相同或更少的权限，则返回 ``True`` 。"""
        if isinstance(other, Permissions):
            return (self.value & other.value) == self.value
        else:
            raise TypeError(f"cannot compare {self.__class__.__name__} with {other.__class__.__name__}")

    def is_superset(self, other: Permissions) -> bool:
        """如果 self 与 other 具有相同或更多的权限，则返回 ``True`` 。"""
        if isinstance(other, Permissions):
            return (self.value | other.value) == self.value
        else:
            raise TypeError(f"cannot compare {self.__class__.__name__} with {other.__class__.__name__}")

    def is_strict_subset(self, other: Permissions) -> bool:
        """如果其他权限是自身权限的严格子集，则返回 ``True`` 。"""
        return self.is_subset(other) and self != other

    def is_strict_superset(self, other: Permissions) -> bool:
        """如果 other 上的权限是 self 上的权限的严格超集，则返回 ``True`` 。"""
        return self.is_superset(other) and self != other

    __le__ = is_subset
    __ge__ = is_superset
    __lt__ = is_strict_subset
    __gt__ = is_strict_superset

    @classmethod
    def none(cls: Type[P]) -> P:
        """创建一个 :class:`Permissions` 的工厂方法，所有权限都设置为 ``False`` 。"""
        return cls(0)

    @classmethod
    def all(cls: Type[P]) -> P:
        """创建一个 :class:`Permissions` 的工厂方法，所有权限都设置为 ``True``。
        """
        return cls(0b111)

    def update(self, **kwargs: bool) -> None:
        r"""批量更新此权限对象。
        允许你使用关键字参数设置多个属性。名称必须与列出的属性相同。无关的键值对将被默默忽略。

        Parameters
        ------------
        \*\*kwargs
            用于批量更新权限的键/值对列表。
        """
        for key, value in kwargs.items():
            if key in self.VALID_FLAGS:
                setattr(self, key, value)

    def handle_overwrite(self, allow: int, deny: int) -> None:
        # 基本上这就是这里发生的事情。
        # 我们有一个原始的位数组，例如1010
        # 然后我们有另一个被“拒绝”的位数组，例如1111
        # 然后我们有最后一个“允许”的，例如0101
        # 我们希望原始 OP 被拒绝最终导致被拒绝的任何内容都被设置为 0。
        # 所以 1010 OP 1111 -> 0000
        # 然后我们取这个值并查看允许的值。
        # 并且允许的设置为 1。
        # 所以 0000 OP2 0101 -> 0101
        # OP 是  原始 & ~拒绝。
        # OP2 是 原始 | 允许。
        self.value = (self.value & ~deny) | allow

    @flag_value
    def read_messages(self) -> int:
        """:class:`bool`: 如果用户可以从所有或特定文本频道读取消息，则返回 ``True`` 。"""
        return 1 << 0

    @make_permission_alias('read_messages')
    def view_channel(self) -> int:
        """:class:`bool`: :attr:`read_messages` 的别名。
        """
        return 1 << 0

    @flag_value
    def manage_channels(self) -> int:
        """:class:`bool`: 如果用户可以在公会中编辑、删除或创建频道，则返回 ``True`` 。
        """
        return 1 << 1

    @flag_value
    def send_messages(self) -> int:
        """:class:`bool`: 如果用户可以从所有或特定文本频道发送消息，则返回 ``True``。"""
        return 1 << 2


PO = TypeVar('PO', bound='PermissionOverwrite')


def _augment_from_permissions(cls):
    cls.VALID_NAMES = set(Permissions.VALID_FLAGS)
    aliases = set()

    # make descriptors for all the valid names and aliases
    for name, value in Permissions.__dict__.items():
        if isinstance(value, permission_alias):
            key = value.alias
            aliases.add(name)
        elif isinstance(value, flag_value):
            key = name
        else:
            continue

        # god bless Python
        def getter(self, x=key):
            return self._values.get(x)

        def setter(self, value, x=key):
            self._set(x, value)

        prop = property(getter, setter)
        setattr(cls, name, prop)

    cls.PURE_FLAGS = cls.VALID_NAMES - aliases
    return cls


@_augment_from_permissions
class PermissionOverwrite:
    r"""用于表示特定于子频道的权限的类型。
    与常规的 :class:`Permissions`\ 不同，权限的默认值相当于 ``None`` 而不是 ``False`` 。
    将值设置为 ``False`` 是 **明确主动拒绝** 该权限，
    将值设置为 ``True`` 是 **明确主动允许** 该权限。

    它支持的值与 :class:`Permissions` 相同，但增加了将其设置为 ``None`` 的可能性。

    .. container:: operations

        .. describe:: x == y

            检查两个覆盖是否相等。

        .. describe:: x != y

            检查两个覆盖是否不相等。

        .. describe:: iter(x)

           返回 ``(perm, value)`` 对的迭代器。例如，这允许将其构造为字典或列表。请注意，未显示别名。

    Parameters
    -----------
    \*\*kwargs
        按名称设置权限值。
    """

    __slots__ = ('_values',)

    if TYPE_CHECKING:
        VALID_NAMES: ClassVar[Set[str]]
        PURE_FLAGS: ClassVar[Set[str]]
        # I wish I didn't have to do this
        read_messages: Optional[bool]
        view_channel: Optional[bool]
        manage_channels: Optional[bool]
        send_messages: Optional[bool]

    def __init__(self, **kwargs: Optional[bool]):
        self._values: Dict[str, Optional[bool]] = {}

        for key, value in kwargs.items():
            if key not in self.VALID_NAMES:
                raise ValueError(f'没有名为 {key} 的权限。')

            setattr(self, key, value)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, PermissionOverwrite) and self._values == other._values

    def _set(self, key: str, value: Optional[bool]) -> None:
        if value not in (True, None, False):
            raise TypeError(f'预期 bool 或 NoneType，收到 {value.__class__.__name__}')

        if value is None:
            self._values.pop(key, None)
        else:
            self._values[key] = value

    def pair(self) -> Tuple[Permissions, Permissions]:
        """Tuple[:class:`Permissions`, :class:`Permissions`]: 从此覆盖返回 (allow, deny) 对。"""

        allow = Permissions.none()
        deny = Permissions.none()

        for key, value in self._values.items():
            if value is True:
                setattr(allow, key, True)
            elif value is False:
                setattr(deny, key, True)

        return allow, deny

    @classmethod
    def from_pair(cls: Type[PO], allow: Permissions, deny: Permissions) -> PO:
        """从允许拒绝的 :class:`Permissions` 对创建覆盖。"""
        ret = cls()
        for key, value in allow:
            if value is True:
                setattr(ret, key, True)

        for key, value in deny:
            if value is True:
                setattr(ret, key, False)

        return ret

    def is_empty(self) -> bool:
        """检查权限覆盖当前是否为空。空权限覆盖是没有设置为 ``True`` 或 ``False`` 的覆盖。

        Returns
        -------
        :class:`bool`
            指示覆盖是否为空。
        """
        return len(self._values) == 0

    def update(self, **kwargs: bool) -> None:
        r"""批量更新此权限覆盖对象。允许你使用关键字参数设置多个属性。名称必须与列出的属性相同。无关的键值对将被默默忽略。

        Parameters
        ------------
        \*\*kwargs
            用于批量更新的键值对列表。
        """
        for key, value in kwargs.items():
            if key not in self.VALID_NAMES:
                continue

            setattr(self, key, value)

    def __iter__(self) -> Iterator[Tuple[str, Optional[bool]]]:
        for key in self.PURE_FLAGS:
            yield key, self._values.get(key)
