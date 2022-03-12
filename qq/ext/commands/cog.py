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

import inspect
from typing import Any, Callable, ClassVar, Dict, Generator, List, Optional, TYPE_CHECKING, Tuple, TypeVar, Type

import qq.utils
from ._types import _BaseCommand

if TYPE_CHECKING:
    from .bot import BotBase
    from .context import Context
    from .core import Command

__all__ = (
    'CogMeta',
    'Cog',
)

CogT = TypeVar('CogT', bound='Cog')
FuncT = TypeVar('FuncT', bound=Callable[..., Any])

MISSING: Any = qq.utils.MISSING


class CogMeta(type):
    """用于定义齿轮的元类。

    请注意，你大概不应该直接使用它。
    它纯粹是为了文档目的而公开的，同时使自定义元类与其他元类混合，例如 :class:`abc.ABCMeta` 元类。

    例如，要创建一个抽象的 cog mixin 类，将执行以下操作。

    .. code-block:: python3

        import abc

        class CogABCMeta(commands.CogMeta, abc.ABCMeta):
            pass

        class SomeMixin(metaclass=abc.ABCMeta):
            pass

        class SomeCogMixin(SomeMixin, commands.Cog, metaclass=CogABCMeta):
            pass

    .. note::

        当传递下面记录的元类的属性时，请注意你必须将其作为仅关键字参数传递给类创建，如下例所示：

        .. code-block:: python3

            class MyCog(commands.Cog, name='My Cog'):
                pass

    Attributes
    -----------
    name: :class:`str`
        齿轮名称。 默认情况下，它是没有修改的类的名称。
    description: :class:`str`
        齿轮描述。 默认情况下，它是类的文档字符串。


    command_attrs: :class:`dict`
        应用于此齿轮中每个命令的属性列表。
        字典将被传递到 __init__ 处的 :class:`Command` 选项。
        如果你在类中的命令属性内指定属性，它将覆盖此属性内指定的属性。 例如：

        .. code-block:: python3

            class MyCog(commands.Cog, command_attrs=dict(hidden=True)):
                @commands.command()
                async def foo(self, ctx):
                    pass # hidden -> True

                @commands.command(hidden=False)
                async def bar(self, ctx):
                    pass # hidden -> False
    """
    __cog_name__: str
    __cog_settings__: Dict[str, Any]
    __cog_commands__: List[Command]
    __cog_listeners__: List[Tuple[str, str]]

    def __new__(cls: Type[CogMeta], *args: Any, **kwargs: Any) -> CogMeta:
        name, bases, attrs = args
        attrs['__cog_name__'] = kwargs.pop('name', name)
        attrs['__cog_settings__'] = kwargs.pop('command_attrs', {})

        description = kwargs.pop('description', None)
        if description is None:
            description = inspect.cleandoc(attrs.get('__doc__', ''))
        attrs['__cog_description__'] = description

        commands = {}
        listeners = {}
        no_bot_cog = '命令或侦听器不得以 cog_ 或 bot_ 开头（在方法 {0.__name__}.{1} 中）'

        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
        for base in reversed(new_cls.__mro__):
            for elem, value in base.__dict__.items():
                if elem in commands:
                    del commands[elem]
                if elem in listeners:
                    del listeners[elem]

                is_static_method = isinstance(value, staticmethod)
                if is_static_method:
                    value = value.__func__
                if isinstance(value, _BaseCommand):
                    if is_static_method:
                        raise TypeError(f'方法 {base}.{elem!r} 中的命令不能是静态方法。')
                    if elem.startswith(('cog_', 'bot_')):
                        raise TypeError(no_bot_cog.format(base, elem))
                    commands[elem] = value
                elif inspect.iscoroutinefunction(value):
                    try:
                        getattr(value, '__cog_listener__')
                    except AttributeError:
                        continue
                    else:
                        if elem.startswith(('cog_', 'bot_')):
                            raise TypeError(no_bot_cog.format(base, elem))
                        listeners[elem] = value

        new_cls.__cog_commands__ = list(commands.values())  # this will be copied in Cog.__new__

        listeners_as_list = []
        for listener in listeners.values():
            for listener_name in listener.__cog_listener_names__:
                # I use __name__ instead of just storing the value so I can inject
                # the self attribute when the time comes to add them to the bot
                listeners_as_list.append((listener_name, listener.__name__))

        new_cls.__cog_listeners__ = listeners_as_list
        return new_cls

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args)

    @classmethod
    def qualified_name(cls) -> str:
        return cls.__cog_name__


def _cog_special_method(func: FuncT) -> FuncT:
    func.__cog_special_method__ = None
    return func


class Cog(metaclass=CogMeta):
    """所有齿轮必须继承的基类。

    齿轮是命令、侦听器和可选状态的集合，可帮助将命令组合在一起。关于它们的更多信息可以在 :ref:`ext_commands_cogs` 页面上找到。

    从此类继承时，CogMeta 中显示的选项在这里同样有效。
    """
    __cog_name__: ClassVar[str]
    __cog_settings__: ClassVar[Dict[str, Any]]
    __cog_commands__: ClassVar[List[Command]]
    __cog_listeners__: ClassVar[List[Tuple[str, str]]]

    def __new__(cls: Type[CogT], *args: Any, **kwargs: Any) -> CogT:
        # For issue 426, we need to store a copy of the command objects
        # since we modify them to inject `self` to them.
        # To do this, we need to interfere with the Cog creation process.
        self = super().__new__(cls)
        cmd_attrs = cls.__cog_settings__

        # Either update the command with the cog provided defaults or copy it.
        # r.e type ignore, type-checker complains about overriding a ClassVar
        self.__cog_commands__ = tuple(c._update_copy(cmd_attrs) for c in cls.__cog_commands__)  # type: ignore

        lookup = {
            cmd.qualified_name: cmd
            for cmd in self.__cog_commands__
        }

        # Update the Command instances dynamically as well
        for command in self.__cog_commands__:
            setattr(self, command.callback.__name__, command)
            parent = command.parent
            if parent is not None:
                # Get the latest parent reference
                parent = lookup[parent.qualified_name]  # type: ignore

                # Update our parent's reference to our self
                parent.remove_command(command.name)  # type: ignore
                parent.add_command(command)  # type: ignore

        return self

    def get_commands(self) -> List[Command]:
        r"""
        Returns
        --------
        List[:class:`.Command`]
            在这个齿轮中定义的 :class:`.Command`\s 的 :class:`list`。

            .. note::

                这不包括子命令。
        """
        return [c for c in self.__cog_commands__ if c.parent is None]

    @property
    def qualified_name(self) -> str:
        """:class:`str`: 返回齿轮的指定名称，而不是类名称。"""
        return self.__cog_name__

    @property
    def description(self) -> str:
        """:class:`str`: 返回齿轮的描述，通常是清理过的文档字符串。"""
        return self.__cog_description__

    @description.setter
    def description(self, description: str) -> None:
        self.__cog_description__ = description

    def walk_commands(self) -> Generator[Command, None, None]:
        """递归遍历此齿轮的命令和子命令的迭代器。

        Yields
        ------
        Union[:class:`.Command`, :class:`.Group`]
            来自齿轮的命令或命令组。
        """
        from .core import GroupMixin
        for command in self.__cog_commands__:
            if command.parent is None:
                yield command
                if isinstance(command, GroupMixin):
                    yield from command.walk_commands()

    def get_listeners(self) -> List[Tuple[str, Callable[..., Any]]]:
        """返回在此齿轮中定义的侦听器的列表。

        Returns
        --------
        List[Tuple[:class:`str`, :ref:`coroutine <coroutine>`]]
            此齿轮中定义的侦听器。
        """
        return [(name, getattr(self, method_name)) for name, method_name in self.__cog_listeners__]

    @classmethod
    def _get_overridden_method(cls, method: FuncT) -> Optional[FuncT]:
        """如果该方法未被覆盖，则返回 None 。否则返回被覆盖的方法。"""
        return getattr(method.__func__, '__cog_special_method__', method)

    @classmethod
    def listener(cls, name: str = MISSING) -> Callable[[FuncT], FuncT]:
        """将函数标记为侦听器的装饰器。

        这是 :meth:`.Bot.listen` 的齿轮版本。

        Parameters
        ------------
        name: :class:`str`
            正在侦听的事件的名称。如果未提供，则默认为函数名称。

        Raises
        --------
        TypeError
            该函数不是协程函数或未将字符串作为名称传递。
        """

        if name is not MISSING and not isinstance(name, str):
            raise TypeError(f'Cog.listener 预期 str 但收到 {name.__class__.__name__!r} 。')

        def decorator(func: FuncT) -> FuncT:
            actual = func
            if isinstance(actual, staticmethod):
                actual = actual.__func__
            if not inspect.iscoroutinefunction(actual):
                raise TypeError('监听器函数必须是协程函数。')
            actual.__cog_listener__ = True
            to_assign = name or actual.__name__
            try:
                actual.__cog_listener_names__.append(to_assign)
            except AttributeError:
                actual.__cog_listener_names__ = [to_assign]
            # we have to return `func` instead of `actual` because
            # we need the type to be `staticmethod` for the metaclass
            # to pick it up but the metaclass unfurls the function and
            # thus the assignments need to be on the actual function
            return func

        return decorator

    def has_error_handler(self) -> bool:
        """:class:`bool`: 检查齿轮是否有错误处理程序。
        """
        return not hasattr(self.cog_command_error.__func__, '__cog_special_method__')

    @_cog_special_method
    def cog_unload(self) -> None:
        """当齿轮被移除时调用的特殊方法。

        此函数 **不能** 是协程。它必须是一个常规函数。

        如果子类想要特殊的卸载行为，它们必须替换它。
        """
        pass

    @_cog_special_method
    def bot_check_once(self, ctx: Context) -> bool:
        """注册为 :meth:`.Bot.check_once` 检查的特殊方法。

        这个函数 **可以** 是一个协程，并且必须采用一个唯一的参数 ``ctx`` 来表示 :class:`.Context`。
        """
        return True

    @_cog_special_method
    def bot_check(self, ctx: Context) -> bool:
        """注册为 :meth:`.Bot.check` 检查的特殊方法。

        这个函数 **可以** 是一个协程，并且必须采用一个唯一的参数 ``ctx`` 来表示 :class:`.Context`。
        """
        return True

    @_cog_special_method
    def cog_check(self, ctx: Context) -> bool:
        """一个特殊的方法，为这个齿轮中的每个命令和子命令注册为 :func:`~qq.ext.commands.check`。

        这个函数 **可以** 是一个协程，并且必须采用一个唯一的参数 ``ctx`` 来表示 :class:`.Context`。
        """
        return True

    @_cog_special_method
    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        """每当在此齿轮内分派错误时调用的特殊方法。

        除了仅应用于此齿轮内的命令，这与 :func:`.on_command_error` 类似，。

        这 **必须** 是一个协程。

        Parameters
        -----------
        ctx: :class:`.Context`
            发生错误的调用 context 。
        error: :class:`CommandError`
            发生的错误。
        """
        pass

    @_cog_special_method
    async def cog_before_invoke(self, ctx: Context) -> None:
        """作为齿轮本地调用前钩的特殊方法。

        这类似于 :meth:`.Command.before_invoke` 。

        这 **必须** 是一个协程。

        Parameters
        -----------
        ctx: :class:`.Context`
            调用 context 。
        """
        pass

    @_cog_special_method
    async def cog_after_invoke(self, ctx: Context) -> None:
        """作为齿轮本地调用后钩的特殊方法。
        
        这类似于:meth:`.Command.after_invoke`。
        
        这 **必须** 是一个协程。

        Parameters
        -----------
        ctx: :class:`.Context`
            调用 context 。
        """
        pass

    def _inject(self: CogT, bot: BotBase) -> CogT:
        cls = self.__class__

        # realistically, the only thing that can cause loading errors
        # is essentially just the command loading, which raises if there are
        # duplicates. When this condition is met, we want to undo all what
        # we've added so far for some form of atomic loading.
        for index, command in enumerate(self.__cog_commands__):
            command.cog = self
            if command.parent is None:
                try:
                    bot.add_command(command)
                except Exception as e:
                    # undo our additions
                    for to_undo in self.__cog_commands__[:index]:
                        if to_undo.parent is None:
                            bot.remove_command(to_undo.name)
                    raise e

        # check if we're overriding the default
        if cls.bot_check is not Cog.bot_check:
            bot.add_check(self.bot_check)

        if cls.bot_check_once is not Cog.bot_check_once:
            bot.add_check(self.bot_check_once, call_once=True)

        # while Bot.add_listener can raise if it's not a coroutine,
        # this precondition is already met by the listener decorator
        # already, thus this should never raise.
        # Outside of, memory errors and the like...
        for name, method_name in self.__cog_listeners__:
            bot.add_listener(getattr(self, method_name), name)

        return self

    def _eject(self, bot: BotBase) -> None:
        cls = self.__class__

        try:
            for command in self.__cog_commands__:
                if command.parent is None:
                    bot.remove_command(command.name)

            for _, method_name in self.__cog_listeners__:
                bot.remove_listener(getattr(self, method_name))

            if cls.bot_check is not Cog.bot_check:
                bot.remove_check(self.bot_check)

            if cls.bot_check_once is not Cog.bot_check_once:
                bot.remove_check(self.bot_check_once, call_once=True)
        finally:
            try:
                self.cog_unload()
            except Exception:
                pass
