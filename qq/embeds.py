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

import datetime
from typing import Any, Dict, Final, List, Mapping, Protocol, TYPE_CHECKING, Type, TypeVar, Union, Optional

__all__ = (
    'Embed',
    'Ark'
)

from . import utils
from .colour import Colour


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


class Ark:
    """代表一个 QQ Ark。

    .. container:: operations

        .. describe:: len(x)

            返回嵌入的总大小。用于检查它是否在 6000 个字符限制内。

        .. describe:: bool(b)

            返回嵌入是否有任何数据集。

    Attributes
    -----------
    template_id: :class:`str`
        要使用的模版 ID。
    colour: Union[:class:`Colour`, :class:`int`]
        嵌入的颜色代码。别名为 ``color``。这可以在初始化期间设置。目前官方还没有实现
    """
    __slots__ = (
        '_fields',
        '_colour',
        'template_id',
        'colour',
        '_extra'
    )

    def __init__(
            self,
            *,
            colour: Optional[Union[int, Colour, _EmptyEmbed]] = EmptyEmbed,
            color: Optional[Union[int, Colour, _EmptyEmbed]] = EmptyEmbed,
            template_id: int,
    ):
        self._extra = {}
        self.template_id = template_id
        self.colour = colour if colour is not EmptyEmbed else color if color is not EmptyEmbed else None

    @property
    def fields(self) -> List[_EmbedFieldProxy]:
        """List[Union[``EmbedProxy``, :attr:`Empty`]]:
        返回 ``EmbedProxy`` 的一个列表，表示字段内容。有关你可以访问的可能值，请参阅 :meth:`add_field`。
        如果该属性没有值，则返回 :attr:`Empty`。
        """
        return [EmbedProxy(d) for d in getattr(self, '_fields', [])]  # type: ignore

    def set_attribute(self: E, key: Any, value: Any) -> E:
        """向 Ark 对象添加字段。此函数返回类实例以允许流式链接。

        Parameters
        -----------
        key: :class:`str`
            字段的名称。
        value: :class:`str`
            字段的值。
        """

        self._extra[str(key)] = str(value)
        return self

    def add_field(self: E, *, desc: Any, url: Any = None) -> E:
        """向 Ark 对象添加字段。此函数返回类实例以允许流式链接。

        Parameters
        -----------
        desc: :class:`str`
            字段的值。
        url: :class:`str`
            字段的 Url。
        """

        field = {'obj_kv': []}
        if desc:
            field['obj_kv'].append({
                "key": "desc",
                "value": str(desc)
            })
        if url:
            field['obj_kv'].append({
                "key": "url",
                "value": str(desc)
            })

        try:
            self._fields.append(field)  # type: ignore
        except AttributeError:
            self._fields = [field]

        return self

    def insert_field_at(self: E, index: int, *, desc: Any, url: Any = None) -> E:
        """在 Ark 的指定索引之前插入一个字段。此函数返回类实例以允许流式链接。

        Parameters
        -----------
        index: :class:`int`
            插入字段的位置的索引。
        desc: :class:`str`
            字段的值。
        url: :class:`str`
            字段的 Url。
        """

        field = {'obj_kv': []}
        if desc:
            field['obj_kv'].append({
                "key": "desc",
                "value": str(desc)
            })
        if url:
            field['obj_kv'].append({
                "key": "link",
                "value": str(desc)
            })

        try:
            self._fields.insert(index, field)  # type: ignore
        except AttributeError:
            self._fields = [field]

        return self

    def clear_fields(self) -> None:
        """从此 Ark 中删除所有字段。"""
        try:
            self._fields.clear()
        except AttributeError:
            self._fields = []

    def to_dict(self) -> EmbedData:
        """将此 Ark 对象转换为字典。"""

        result = {"template_id": self.template_id,
                  "kv": [{"key": i, "value": j} for i, j in self._extra.items()]}

        if self.fields:
            result["kv"].append({"key": "#LIST#", "obj": self._fields})  # type: ignore

        return result  # type: ignore


class Embed:
    """代表一个 QQ 嵌入。

    .. container:: operations

        .. describe:: len(x)

            返回嵌入的总大小。用于检查它是否在 6000 个字符限制内。

        .. describe:: bool(b)

            返回嵌入是否有任何数据集。

    某些属性返回一个 ``EmbedProxy`` ，
    除了使用点访问，该类型的行为类似于常规 :class:`dict`，例如 ``embed.author.icon_url``。
    如果属性无效或为空，则返回一个特殊的值，:attr:`Embed.Empty`。

    为了便于使用，所有需要 :class:`str` 的参数都为你隐式转换为 :class:`str`。

    Attributes
    -----------
    title: :class:`str`
        嵌入的标题。这可以在初始化期间设置。
    description: :class:`str`
        嵌入的描述。这可以在初始化期间设置。
    timestamp: :class:`datetime.datetime`
        嵌入内容的时间戳。这是一个 aware 的 datetime。如果传递了一个简单的 datetime，它会被转换为具有本地时区的已知 datetime。
    colour: Union[:class:`Colour`, :class:`int`]
        嵌入的颜色代码。别名为 ``color``。这可以在初始化期间设置。目前官方还没有实现
    prompt: :class: `str`
        嵌入的弹出窗口。这可以在初始化期间设置。
    """
    __slots__ = (
        'title',
        '_fields',
        'description',
        'prompt',
        '_fields',
        '_timestamp',
        '_author',
        '_footer',
        '_colour',
        '_thumbnail'
    )

    Empty: Final = EmptyEmbed

    def __init__(
            self,
            *,
            title: MaybeEmpty[Any] = EmptyEmbed,
            colour: Optional[Union[int, Colour, _EmptyEmbed]] = EmptyEmbed,
            color: Optional[Union[int, Colour, _EmptyEmbed]] = EmptyEmbed,
            description: MaybeEmpty[Any] = EmptyEmbed,
            prompt: MaybeEmpty[Any] = EmptyEmbed,
            timestamp: datetime.datetime = None,
    ):
        self.colour = colour if colour is not EmptyEmbed else color if color is not EmptyEmbed else None
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
        """将 :class:`dict` 转换为 :class:`Embed`，前提是它采用 QQ 期望的格式。
        你可以在 ``官方 QQ 文档``__ 中找到有关此格式的信息。

        .. _QQDocs: https://bot.q.qq.com/wiki/develop/api/openapi/message/model.html#messageembed
        __ QQDocs_

        Parameters
        -----------
        data: :class:`dict`
            要转换为嵌入的字典。
        """
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

        # try to fill in the more rich fields

        try:
            self._colour = Colour(value=int(data['color']))
        except KeyError:
            pass

        try:
            self._timestamp = utils.parse_time(data['timestamp'])
        except KeyError:
            pass

        for attr in ('thumbnail', 'video', 'provider', 'author', 'fields', 'image', 'footer'):
            try:
                value = data[attr]
            except KeyError:
                continue
            else:
                setattr(self, '_' + attr, value)

        return self

    def copy(self: E) -> E:
        """返回嵌入的浅表副本。"""
        return self.__class__.from_dict(self.to_dict())

    def __len__(self) -> int:
        total = len(self.title) + len(self.description)
        for field in getattr(self, '_fields', []):
            total += len(field['name']) + len(field['value'])

        try:
            footer_text = self._footer['text']
        except (AttributeError, KeyError):
            pass
        else:
            total += len(footer_text)

        try:
            author = self._author
        except AttributeError:
            pass
        else:
            total += len(author['name'])

        return total

    def __bool__(self) -> bool:
        return any(
            (
                self.title,
                self.description,
                self.colour,
                self.fields,
                self.timestamp,
                self.author,
                self.thumbnail,
                self.footer,
                self.image,
                self.provider,
                self.video,
            )
        )

    @property
    def colour(self) -> MaybeEmpty[Colour]:
        return getattr(self, '_colour', EmptyEmbed)

    @colour.setter
    def colour(self, value: Union[int, Colour, _EmptyEmbed]):  # type: ignore
        if isinstance(value, (Colour, _EmptyEmbed)):
            self._colour = value
        elif isinstance(value, int):
            self._colour = Colour(value=value)
        else:
            raise TypeError(
                f'Expected qq.Colour, int, or Embed.Empty but received {value.__class__.__name__} instead.')

    color = colour

    @property
    def timestamp(self) -> MaybeEmpty[datetime.datetime]:
        return getattr(self, '_timestamp', EmptyEmbed)

    @timestamp.setter
    def timestamp(self, value: MaybeEmpty[datetime.datetime]):
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                value = value.astimezone()
            self._timestamp = value
        elif isinstance(value, _EmptyEmbed):
            self._timestamp = value
        else:
            raise TypeError(
                f"Expected datetime.datetime or Embed.Empty received {value.__class__.__name__} instead")

    @property
    def footer(self) -> _EmbedFooterProxy:
        """返回表示页脚内容的 ``EmbedProxy``。
        请参阅 :meth:`set_footer` 以获取你可以访问的可能值。
        如果该属性没有值，则返回 :attr:`Empty`。


        """
        return EmbedProxy(getattr(self, '_footer', {}))  # type: ignore

    def set_footer(self: E, *, text: MaybeEmpty[Any] = EmptyEmbed, icon_url: MaybeEmpty[Any] = EmptyEmbed) -> E:
        """设置嵌入内容的页脚。此函数返回类实例以允许流式链接。



        Parameters
        -----------
        text: :class:`str`
            页脚文本。
        icon_url: :class:`str`
            页脚图标的 URL。仅支持 HTTP(S)。
        """

        self._footer = {}
        if text is not EmptyEmbed:
            self._footer['text'] = str(text)

        if icon_url is not EmptyEmbed:
            self._footer['icon_url'] = str(icon_url)

        return self

    def remove_footer(self: E) -> E:
        """清除嵌入的页脚信息。此函数返回类实例以允许流式链接。


        """
        try:
            del self._footer
        except AttributeError:
            pass

        return self

    @property
    def image(self) -> _EmbedMediaProxy:
        """返回表示图像内容的 ``EmbedProxy`` 。

        你可以访问的可能属性是：

        - ``url``
        - ``proxy_url``
        - ``width``
        - ``height``

        如果该属性没有值，则返回 :attr:`Empty`。


        """
        return EmbedProxy(getattr(self, '_image', {}))  # type: ignore

    def set_image(self: E, *, url: MaybeEmpty[Any]) -> E:
        """设置嵌入内容的图像。
        此函数返回类实例以允许流式链接。
        传递 :attr:`Empty` 会删除图像。



        Parameters
        -----------
        url: :class:`str`
            图像的源 URL。仅支持 HTTP(S)。
        """

        if url is EmptyEmbed:
            try:
                del self._image
            except AttributeError:
                pass
        else:
            self._image = {
                'url': str(url),
            }

        return self

    @property
    def thumbnail(self) -> _EmbedMediaProxy:
        """返回表示缩略图内容的 ``EmbedProxy`` 。

        你可以访问的可能属性是：

        - ``url``
        - ``proxy_url``
        - ``width``
        - ``height``

        如果该属性没有值，则返回 :attr:`Empty`。


        """
        return EmbedProxy(getattr(self, '_thumbnail', {}))  # type: ignore

    def set_thumbnail(self: E, *, url: MaybeEmpty[Any]) -> E:
        """设置嵌入内容的缩略图。此函数返回类实例以允许流式链接。传递 :attr:`Empty` 会删除缩略图。

        Parameters
        -----------
        url: :class:`str`
            缩略图的源 URL。仅支持 HTTP(S)。


        """

        if url is EmptyEmbed:
            try:
                del self._thumbnail
            except AttributeError:
                pass
        else:
            self._thumbnail = {
                'url': str(url),
            }

        return self

    @property
    def video(self) -> _EmbedVideoProxy:
        """返回表示视频内容的 ``EmbedProxy`` 。

        可能的属性包括：

        - ``url`` 视频网址。
        - ``height`` 视频高度。
        - ``width`` 视频宽度。

        如果该属性没有值，则返回 :attr:`Empty`。


        """
        return EmbedProxy(getattr(self, '_video', {}))  # type: ignore

    @property
    def provider(self) -> _EmbedProviderProxy:
        """返回表示提供者内容的 ``EmbedProxy`` 。
        可能被访问的唯一属性是 ``name`` 和 ``url`` 。如果该属性没有值，则返回 :attr:`Empty`。


        """
        return EmbedProxy(getattr(self, '_provider', {}))  # type: ignore

    @property
    def author(self) -> _EmbedAuthorProxy:
        """返回表示作者内容的 ``EmbedProxy`` 。有关你可以访问的可能值，请参阅 :meth:`set_author`。
        如果该属性没有值，则返回 :attr:`Empty`。


        """
        return EmbedProxy(getattr(self, '_author', {}))  # type: ignore

    def set_author(self: E, *, name: Any, url: MaybeEmpty[Any] = EmptyEmbed,
                   icon_url: MaybeEmpty[Any] = EmptyEmbed) -> E:
        """设置嵌入内容的作者。此函数返回类实例以允许流式链接。

        Parameters
        -----------
        name: :class:`str`
            作者的名字。
        url: :class:`str`
            作者的 URL。
        icon_url: :class:`str`
            作者图标的 URL。仅支持 HTTP(S)。


        """

        self._author = {
            'name': str(name),
        }

        if url is not EmptyEmbed:
            self._author['url'] = str(url)

        if icon_url is not EmptyEmbed:
            self._author['icon_url'] = str(icon_url)

        return self

    def remove_author(self: E) -> E:
        """清除嵌入的作者信息。此函数返回类实例以允许流式链接。
        """
        try:
            del self._author
        except AttributeError:
            pass

        return self

    @property
    def fields(self) -> List[_EmbedFieldProxy]:
        """List[Union[``EmbedProxy``, :attr:`Empty`]]:
        返回 ``EmbedProxy`` 的一个列表，表示字段内容。有关你可以访问的可能值，请参阅 :meth:`add_field`。
        如果该属性没有值，则返回 :attr:`Empty`。
        """
        return [EmbedProxy(d) for d in getattr(self, '_fields', [])]  # type: ignore

    def add_field(self: E, *, name: str, value: Optional[str] = '', inline: bool = True) -> E:
        """向嵌入对象添加字段。此函数返回类实例以允许流式链接。

        Parameters
        -----------
        name: :class:`str`
            字段的名称。
        value: :class:`str`
            字段的值。目前并无作用
        inline: :class:`bool`
            该字段是否应内联显示。目前并无作用
        """

        field = {
            'inline': inline,
            'name': str(name),
            'value': str(value),
        }

        try:
            self._fields.append(field)
        except AttributeError:
            self._fields = [field]

        return self

    def insert_field_at(self: E, index: int, *, name: str, value: Optional[str] = '', inline: bool = True) -> E:
        """在嵌入的指定索引之前插入一个字段。此函数返回类实例以允许流式链接。

        Parameters
        -----------
        index: :class:`int`
            插入字段的位置的索引。
        name: :class:`str`
            字段的名称。
        value: :class:`str`
            字段的值。目前并无作用
        inline: :class:`bool`
            该字段是否应内联显示。目前并无作用
        """

        field = {
            'inline': inline,
            'name': str(name),
            'value': str(value),
        }

        try:
            self._fields.insert(index, field)
        except AttributeError:
            self._fields = [field]

        return self

    def clear_fields(self) -> None:
        """从此嵌入中删除所有字段。"""
        try:
            self._fields.clear()
        except AttributeError:
            self._fields = []

    def remove_field(self, index: int) -> None:
        """删除指定索引处的字段。
        如果索引无效或越界，则错误会被默默吞下。

        .. note::

            当按索引删除一个字段时，其他字段的索引会移动以填补空白，就像常规列表一样。

        Parameters
        -----------
        index: :class:`int`
            要删除的字段的索引。
        """
        try:
            del self._fields[index]
        except (AttributeError, IndexError):
            pass

    def set_field_at(self: E, index: int, *, name: Any, value: Any, inline: bool = True) -> E:
        """修改嵌入对象的字段。索引必须指向一个有效的预先存在的字段。此函数返回类实例以允许流式链接。

        Parameters
        -----------
        index: :class:`int`
            要修改的字段的索引。
        name: :class:`str`
            字段的名称。
        value: :class:`str`
            字段的值。
        inline: :class:`bool`
            该字段是否应内联显示。

        Raises
        -------
        IndexError
            提供了无效的索引。
        """

        try:
            field = self._fields[index]
        except (TypeError, IndexError, AttributeError):
            raise IndexError('field index out of range')

        field['name'] = str(name)
        field['value'] = str(value)
        field['inline'] = inline
        return self

    def to_dict(self) -> EmbedData:
        """将此嵌入对象转换为字典。"""

        # add in the raw data into the dict
        # fmt: off
        result = {
            key[1:]: getattr(self, key)
            for key in self.__slots__
            if key[0] == '_' and hasattr(self, key)
        }
        # fmt: on

        # deal with basic convenience wrappers

        try:
            colour = result.pop('colour')
        except KeyError:
            pass
        else:
            if colour:
                result['color'] = colour.value

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

        if self.prompt:
            result['prompt'] = self.prompt

        if self.title:
            result['title'] = self.title

        return result  # type: ignore
