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

import asyncio
import collections
import collections.abc
import importlib.util
import inspect
import sys
import traceback
import types
from typing import Any, Callable, Mapping, List, Dict, TYPE_CHECKING, Optional, TypeVar, Type, Union

import qq
from . import errors
from .cog import Cog
from .context import Context
from .core import GroupMixin
from .help import HelpCommand, DefaultHelpCommand
from .view import StringView

if TYPE_CHECKING:
    import importlib.machinery

    from qq.message import Message
    from ._types import (
        Check,
        CoroFunc,
    )

__all__ = (
    'when_mentioned',
    'when_mentioned_or',
    'Bot',
    'AutoShardedBot',
)

MISSING: Any = qq.utils.MISSING

T = TypeVar('T')
CFT = TypeVar('CFT', bound='CoroFunc')
CXT = TypeVar('CXT', bound='Context')


def when_mentioned(bot: Union[Bot, AutoShardedBot], msg: Message) -> List[str]:
    """实现与提及的命令前缀等效的可调用对象。

    这些旨在传递到 :attr:`.Bot.command_prefix` 属性。
    """
    # bot.user will never be None when this is called
    return [f'<@{bot.user.id}> ', f'<@!{bot.user.id}> ']  # type: ignore


def when_mentioned_or(*prefixes: str) -> Callable[[Union[Bot, AutoShardedBot], Message], List[str]]:
    """在提及或提供其他前缀时实现的可调用对象。

    这些旨在传递到 :attr:`.Bot.command_prefix` 属性。

    Example
    --------

    .. code-block:: python3

        bot = commands.Bot(command_prefix=commands.when_mentioned_or('!'))


    .. note::

        此可调用对象返回另一个可调用对象，因此如果这是在自定义可调用对象中完成的，则必须调用返回的可调用对象，例如：

        .. code-block:: python3

            async def get_prefix(bot, message):
                extras = await prefixes_for(message.guild) # returns a list
                return commands.when_mentioned_or(*extras)(bot, message)


    See Also
    ----------
    :func:`.when_mentioned`
    """

    def inner(bot, msg):
        r = list(prefixes)
        r = when_mentioned(bot, msg) + r
        return r

    return inner


def _is_submodule(parent: str, child: str) -> bool:
    return parent == child or child.startswith(parent + ".")


class _DefaultRepr:
    def __repr__(self):
        return '<default-help-command>'


_default = _DefaultRepr()


class BotBase(GroupMixin):
    def __init__(self, command_prefix, help_command=_default, description=None, **options):
        super().__init__(**options)
        self.command_prefix = command_prefix
        self.extra_events: Dict[str, List[CoroFunc]] = {}
        self.__cogs: Dict[str, Cog] = {}
        self.__extensions: Dict[str, types.ModuleType] = {}
        self._checks: List[Check] = []
        self._check_once = []
        self._before_invoke = None
        self._after_invoke = None
        self._help_command = None
        self.description = inspect.cleandoc(description) if description else ''
        self.owner_id = options.get('owner_id')
        self.owner_ids = options.get('owner_ids', set())
        self.strip_after_prefix = options.get('strip_after_prefix', False)

        if self.owner_id and self.owner_ids:
            raise TypeError('owner_id 和 owner_ids 都被设置。')

        if self.owner_ids and not isinstance(self.owner_ids, collections.abc.Collection):
            raise TypeError(f'owner_ids 必须是一个集合，而不是 {self.owner_ids.__class__!r}')

        if help_command is _default:
            self.help_command = DefaultHelpCommand()
        else:
            self.help_command = help_command

    # internal helpers

    def dispatch(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        # super() will resolve to Client
        super().dispatch(event_name, *args, **kwargs)  # type: ignore
        ev = 'on_' + event_name
        for event in self.extra_events.get(ev, []):
            self._schedule_event(event, ev, *args, **kwargs)  # type: ignore

    @qq.utils.copy_doc(qq.Client.close)
    async def close(self) -> None:
        for extension in tuple(self.__extensions):
            try:
                self.unload_extension(extension)
            except Exception:
                pass

        for cog in tuple(self.__cogs):
            try:
                self.remove_cog(cog)
            except Exception:
                pass

        await super().close()  # type: ignore

    async def on_command_error(self, context: Context, exception: errors.CommandError) -> None:
        """|coro|

        机器人提供的默认命令错误处理程序。

        默认情况下，这会打印到 :data:`sys.stderr` 但是它可以被覆盖以使用不同的实现。

        仅当你没有为命令错误指定任何监听器时才会触发。
        """
        if self.extra_events.get('on_command_error', None):
            return

        command = context.command
        if command and command.has_error_handler():
            return

        cog = context.cog
        if cog and cog.has_error_handler():
            return

        print(f'忽略命令 {context.command} 中的异常：', file=sys.stderr)
        traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stderr)

    # global check registration

    def check(self, func: T) -> T:
        r"""向机器人添加全局检查的装饰器。

        全局检查类似于基于每个命令应用的 :func:`.check`，不同之处在于它在任何命令检查被验证之前运行并适用于机器人拥有的每个命令。

        .. note::

            此函数可以是常规函数或协程。

        类似于命令 :func:`.check` ，它接受一个类型为 :class:`.Context` 的参数，并且只能引发从 :exc:`.CommandError` 继承的异常。

        Example
        ---------

        .. code-block:: python3

            @bot.check
            def check_commands(ctx):
                return ctx.command.qualified_name in allowed_commands

        """
        # T was used instead of Check to ensure the type matches on return
        self.add_check(func)  # type: ignore
        return func

    def add_check(self, func: Check, *, call_once: bool = False) -> None:
        """向机器人添加全局检查。

        这是 :meth:`.check` 和 :meth:`.check_once` 的非装饰器接口。

        Parameters
        -----------
        func
            用作全局检查的函数。
        call_once: :class:`bool`
            如果为 ``True`` 每个 :meth:`.invoke` 调用只应调用一次该函数。
        """

        if call_once:
            self._check_once.append(func)
        else:
            self._checks.append(func)

    def remove_check(self, func: Check, *, call_once: bool = False) -> None:
        """从机器人中删除全局检查。

        此函数是幂等的，如果该函数不在全局检查中，则不会引发异常。

        Parameters
        -----------
        func
            要从全局检查中删除的函数。
        call_once: :class:`bool`
            如果函数是在 :meth:`.Bot.add_check` 调用中添加了 ``call_once=True`` 或使用 :meth:`.check_once`。
        """
        l = self._check_once if call_once else self._checks

        try:
            l.remove(func)
        except ValueError:
            pass

    def check_once(self, func: CFT) -> CFT:
        r"""向机器人添加 ``调用一次`` 全局检查的装饰器。

        与常规的全局检查不同，每个 :meth:`.invoke` 调用只调用一次。

        每当调用命令或调用 :meth:`.Command.can_run` 时，都会调用常规的全局检查。
        这种类型的检查绕过它并确保它只被调用一次，即使在默认的帮助命令中也是如此。

        .. note::

            使用此函数时，发送到组子命令的 :class:`.Context` 可能只解析父命令而不解析子命令，因为它在每个 :meth:`.Bot.invoke` 调用中被调用一次。

        .. note::

            此函数可以是常规函数或协程。

        类似于命令 :func:`.check`，它接受一个类型为 :class:`.Context` 的参数，并且只能引发从 :exc:`.CommandError` 继承的异常。

        Example
        ---------

        .. code-block:: python3

            @bot.check_once
            def whitelist(ctx):
                return ctx.message.author.id in my_whitelist

        """
        self.add_check(func, call_once=True)
        return func

    async def can_run(self, ctx: Context, *, call_once: bool = False) -> bool:
        data = self._check_once if call_once else self._checks

        if len(data) == 0:
            return True

        # type-checker doesn't distinguish between functions and methods
        return await qq.utils.async_all(f(ctx) for f in data)  # type: ignore

    async def is_owner(self, user: qq.User) -> bool:
        """|coro|

        检查 :class:`~qq.User` 或 :class:`~qq.Member` 是否是这个机器人的所有者。

        如果 :attr:`owner_id` 未设置，则会通过使用 :meth:`~.Bot.application_info` 自动获取。

        如果 :attr:`owner_ids` 未设置，该函数还会检查应用程序是否为团队所有。

        Parameters
        -----------
        user: :class:`.abc.User`
            要检查的用户。

        Returns
        --------
        :class:`bool`
            用户是否为所有者。
        """

        if self.owner_id:
            return user.id == self.owner_id
        return user.id in self.owner_ids

    def before_invoke(self, coro: CFT) -> CFT:
        """将协程注册为调用前钩的装饰器。

        在调用命令之前直接调用调用前钩。 这使得它成为设置数据库连接或所需的任何类型的设置的有用功能。

        这个调用前钩有一个唯一的参数，一个 :class:`.Context`。

        .. note::

            :meth:`~.Bot.before_invoke` 和 :meth:`~.Bot.after_invoke` 钩子只有在所有检查和参数解析过程无错误通过时才会被调用。
            如果任何检查或参数解析过程失败，则不会调用挂钩。

        Parameters
        -----------
        coro: :ref:`coroutine <coroutine>`
            要注册为调用前钩的协程。

        Raises
        -------
        TypeError
            传递的协程实际上并不是协程。
        """
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('调用前钩必须是一个协程。')

        self._before_invoke = coro
        return coro

    def after_invoke(self, coro: CFT) -> CFT:
        r"""将协程注册为调用后钩的装饰器。

        在调用命令后直接调用调用后钩。 这使其成为清理数据库连接或任何类型的清理所需的有用功能。

        这个调用后钩有一个唯一的参数，一个 :class:`.Context`。

        .. note::

            类似于 :meth:`~.Bot.before_invoke`\，除非检查和参数解析过程成功，否则不会调用它。
            但是，无论内部命令回调是否引发错误（即 :exc:`.CommandInvokeError`\），都会 **始终** 调用此钩子。
            这使其成为清理的理想选择。

        Parameters
        -----------
        coro: :ref:`coroutine <coroutine>`
            要注册为调用后钩的协程。

        Raises
        -------
        TypeError
            传递的协程实际上并不是协程。
        """
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('调用后钩必须是一个协程。')

        self._after_invoke = coro
        return coro

    # listener registration

    def add_listener(self, func: CoroFunc, name: str = MISSING) -> None:
        """:meth:`.listen` 的非装饰器替代品。

        Parameters
        -----------
        func: :ref:`coroutine <coroutine>`
            要调用的函数。
        name: :class:`str`
            要监听的事件的名称。 默认为 ``func.__name__`` 。

        Example
        --------

        .. code-block:: python3

            async def on_ready(): pass
            async def my_message(message): pass

            bot.add_listener(on_ready)
            bot.add_listener(my_message, 'on_message')

        """
        name = func.__name__ if name is MISSING else name

        if not asyncio.iscoroutinefunction(func):
            raise TypeError('监听器必须是协程')

        if name in self.extra_events:
            self.extra_events[name].append(func)
        else:
            self.extra_events[name] = [func]

    def remove_listener(self, func: CoroFunc, name: str = MISSING) -> None:
        """从监听器池中删除一个监听器。

        Parameters
        -----------
        func
            用作要删除的监听器的函数。
        name: :class:`str`
            要删除的事件的名称。 默认为 ``func.__name__`` 。
        """

        name = func.__name__ if name is MISSING else name

        if name in self.extra_events:
            try:
                self.extra_events[name].remove(func)
            except ValueError:
                pass

    def listen(self, name: str = MISSING) -> Callable[[CFT], CFT]:
        """将另一个函数注册为外部事件监听器的装饰器。
        基本上，这允许你收听来自不同地方的多个事件，例如 :func:`.on_ready`

        被监听的函数必须是一个 :ref:`coroutine <coroutine>` 。

        Example
        --------

        .. code-block:: python3

            @bot.listen()
            async def on_message(message):
                print('one')

            # 在其他文件中...

            @bot.listen('on_message')
            async def my_message(message):
                print('two')

        将以未指定的顺序输出一和二。

        Raises
        -------
        TypeError
            被监听的函数不是协程。
        """

        def decorator(func: CFT) -> CFT:
            self.add_listener(func, name)
            return func

        return decorator

    # cogs

    def add_cog(self, cog: Cog, *, override: bool = False) -> None:
        """向机器人添加一个 ``齿轮`` 。

        齿轮是一个拥有自己的事件监听器和命令的类。

        Parameters
        -----------
        cog: :class:`.Cog`
            注册到机器人的齿轮。
        override: :class:`bool`
            如果之前加载的同名 cog 应该被覆盖而不是引发错误。

        Raises
        -------
        TypeError
            齿轮不是从 :class:`.Cog` 继承的。
        CommandError
            加载过程中发生错误。
        .ClientException
            已加载同名的齿轮。
        """

        if not isinstance(cog, Cog):
            raise TypeError('齿轮必须继承自 Cog')

        cog_name = cog.__cog_name__
        existing = self.__cogs.get(cog_name)

        if existing is not None:
            if not override:
                raise qq.ClientException(f'名为 {cog_name!r} 的 Cog 已加载')
            self.remove_cog(cog_name)

        cog = cog._inject(self)
        self.__cogs[cog_name] = cog

    def get_cog(self, name: str) -> Optional[Cog]:
        """获取请求的齿轮实例。

        如果没有找到齿轮，则返回 ``None`` 。

        Parameters
        -----------
        name: :class:`str`
            你请求的齿轮的名称。
            这相当于在类创建中通过关键字参数传递的名称或在未指定参数的时候为类名称。

        Returns
        --------
        Optional[:class:`Cog`]
            请求的齿轮。 如果未找到，则返回 ``None`` 。
        """
        return self.__cogs.get(name)

    def remove_cog(self, name: str) -> Optional[Cog]:
        """从机器人中移除一个齿轮并返回它。

        齿轮注册的所有注册命令和事件监听器也将被删除。

        如果未找到齿轮，则此方法无效。

        Parameters
        -----------
        name: :class:`str`
            要移除的齿轮的名称。

        Returns
        -------
        Optional[:class:`.Cog`]
             被移除的齿轮。 如果未找到，则为 ``None`` 。
        """

        cog = self.__cogs.pop(name, None)
        if cog is None:
            return

        help_command = self._help_command
        if help_command and help_command.cog is cog:
            help_command.cog = None
        cog._eject(self)

        return cog

    @property
    def cogs(self) -> Mapping[str, Cog]:
        """Mapping[:class:`str`, :class:`Cog`]: 齿轮名到齿轮的只读映射。"""
        return types.MappingProxyType(self.__cogs)

    # extensions

    def _remove_module_references(self, name: str) -> None:
        # find all references to the module
        # remove the cogs registered from the module
        for cogname, cog in self.__cogs.copy().items():
            if _is_submodule(name, cog.__module__):
                self.remove_cog(cogname)

        # remove all the commands from the module
        for cmd in self.all_commands.copy().values():
            if cmd.module is not None and _is_submodule(name, cmd.module):
                if isinstance(cmd, GroupMixin):
                    cmd.recursively_remove_all_commands()
                self.remove_command(cmd.name)

        # remove all the listeners from the module
        for event_list in self.extra_events.copy().values():
            remove = []
            for index, event in enumerate(event_list):
                if event.__module__ is not None and _is_submodule(name, event.__module__):
                    remove.append(index)

            for index in reversed(remove):
                del event_list[index]

    def _call_module_finalizers(self, lib: types.ModuleType, key: str) -> None:
        try:
            func = getattr(lib, 'teardown')
        except AttributeError:
            pass
        else:
            try:
                func(self)
            except Exception:
                pass
        finally:
            self.__extensions.pop(key, None)
            sys.modules.pop(key, None)
            name = lib.__name__
            for module in list(sys.modules.keys()):
                if _is_submodule(name, module):
                    del sys.modules[module]

    def _load_from_module_spec(
            self,
            spec: importlib.machinery.ModuleSpec,
            key: str,
            extras: Optional[Dict[str, Any]] = None
    ) -> None:
        # precondition: key not in self.__extensions
        lib = importlib.util.module_from_spec(spec)
        sys.modules[key] = lib
        try:
            spec.loader.exec_module(lib)  # type: ignore
        except Exception as e:
            del sys.modules[key]
            raise errors.ExtensionFailed(key, e) from e

        try:
            setup = getattr(lib, 'setup')
        except AttributeError:
            del sys.modules[key]
            raise errors.NoEntryPointError(key)

        params = inspect.signature(setup).parameters
        has_kwargs = len(params) > 1

        if extras is not None:
            if not has_kwargs:
                raise errors.InvalidSetupArguments(key)
            elif not isinstance(extras, dict):
                raise errors.ExtensionFailed(key, TypeError("Expected 'extras' to be a dictionary"))

        extras = extras or {}
        try:
            setup(self, **extras)
        except Exception as e:
            del sys.modules[key]
            self._remove_module_references(lib.__name__)
            self._call_module_finalizers(lib, key)
            raise errors.ExtensionFailed(key, e) from e
        else:
            self.__extensions[key] = lib

    def _resolve_name(self, name: str, package: Optional[str]) -> str:
        try:
            return importlib.util.resolve_name(name, package)
        except ImportError:
            raise errors.ExtensionNotFound(name)

    def load_extension(
            self,
            name: str,
            *,
            package: Optional[str] = None,
            extras: Optional[Dict[str, Any]] = None
    ) -> None:

        """加载扩展。

        扩展是包含命令、cog 或监听器的 Python 模块。

        扩展必须有一个全局函数，``setup`` 定义为加载扩展时要执行的操作的入口点。 这个入口点必须有一个参数，``bot`` 。

        Parameters
        ------------
        name: :class:`str`
            要加载的扩展名。 如果访问子模块，它必须像常规 Python 导入一样用点分隔。
            例如如果你想导入 ``foo/test.py`` 你可以使用 ``foo.test``  。
        package: Optional[:class:`str`]
            用于解析相对导入的包名。当使用相对路径加载扩展时，这是必需的，例如 ``.foo.test`` 。 默认为 ``None`` 。
        extras: Optional[:class:`dict`]
            kwargs 到要作为关键字参数传递给 cog 的 ``__init__`` 方法的值的映射。

            Usage ::

                # main.py

                bot.load_extensions("cogs.me_cog", extras={"keyword_arg": True})

                # cogs/me_cog.py
                class MeCog(commands.Cog):
                    def __init__(self, bot, keyword_arg):
                        self.bot = bot
                        self.keyword_arg = keyword_arg
                def setup(bot, **kwargs):
                    bot.add_cog(MeCog(bot, **kwargs))

                # 或者
                def setup(bot, keyword_arg):
                    bot.add_cog(MeCog(bot, keyword_arg))

            .. versionadded:: 1.1.0


        Raises
        --------
        ExtensionNotFound
            无法导入扩展。
            如果无法使用提供的 ``package`` 参数解析扩展的名称，也会引发此问题。
        ExtensionAlreadyLoaded
            扩展已经加载。
        NoEntryPointError
            该扩展没有 ``setup`` 函数。
        ExtensionFailed
            扩展程序或其设置函数有执行错误。
        InvalidSetupArguments
            ``load_extension`` 被赋予了 ``extras`` 但 ``setup`` 函数没有接受任何额外的参数。
        """

        name = self._resolve_name(name, package)
        if name in self.__extensions:
            raise errors.ExtensionAlreadyLoaded(name)

        spec = importlib.util.find_spec(name)
        if spec is None:
            raise errors.ExtensionNotFound(name)

        self._load_from_module_spec(spec, name, extras=extras)

    def unload_extension(self, name: str, *, package: Optional[str] = None) -> None:
        """卸载扩展。

        卸载扩展后，所有命令、监听器和齿轮都将从机器人中删除，并且模块将取消导入。

        扩展可以提供一个可选的全局函数 ``teardown`` ，以便在必要时进行杂项清理。
        这个函数接受一个参数， ``bot`` ，类似于 :meth:`~.Bot.load_extension` 中的 ``setup`` 。

        Parameters
        ------------
        name: :class:`str`
            要卸载的扩展名。 如果访问子模块，它必须像常规 Python 导入一样用点分隔。
            例如如果你想导入 ``foo/test.py`` 你可以使用 ``foo.test``  。
        package: Optional[:class:`str`]
            用于解析相对导入的包名。当使用相对路径加载扩展时，这是必需的，例如  ``.foo.test``  。 默认为 ``None`` 。

        Raises
        -------
        ExtensionNotFound
            无法导入扩展。
            如果无法使用提供的 ``package`` 参数解析扩展的名称，也会引发此问题。
        ExtensionNotLoaded
            未加载扩展。
        """

        name = self._resolve_name(name, package)
        lib = self.__extensions.get(name)
        if lib is None:
            raise errors.ExtensionNotLoaded(name)

        self._remove_module_references(lib.__name__)
        self._call_module_finalizers(lib, name)

    def reload_extension(self, name: str, *, package: Optional[str] = None) -> None:
        """以原子性的方式重新加载扩展。

        这会用相同的扩展名替换扩展名，只是刷新了而已。
        除了以原子性的方式完成，这相当于一个 :meth:`unload_extension` 后跟一个 meth:`load_extension` 。
        也就是说，如果操作在重新加载过程中失败，那么机器人将回滚到之前的工作状态。

        Parameters
        ------------
        name: :class:`str`
            要重新加载的扩展名。 如果访问子模块，它必须像常规 Python 导入一样用点分隔。
            例如如果你想导入 ``foo/test.py`` 你可以使用 ``foo.test``  。
        package: Optional[:class:`str`]
            用于解析相对导入的包名。当使用相对路径加载扩展时，这是必需的，例如  ``.foo.test``  。 默认为 ``None`` 。

        Raises
        -------
        ExtensionNotLoaded
            未加载扩展。
        ExtensionNotFound
            无法导入扩展。 如果无法使用提供的 ``package`` 参数解析扩展的名称，也会引发此错误。
        NoEntryPointError
            该扩展没有 ``setup`` 函数。
        ExtensionFailed
            扩展 ``setup`` 函数有一个错误。
        """

        name = self._resolve_name(name, package)
        lib = self.__extensions.get(name)
        if lib is None:
            raise errors.ExtensionNotLoaded(name)

        # get the previous module states from sys modules
        modules = {
            name: module
            for name, module in sys.modules.items()
            if _is_submodule(lib.__name__, name)
        }

        try:
            # Unload and then load the module...
            self._remove_module_references(lib.__name__)
            self._call_module_finalizers(lib, name)
            self.load_extension(name)
        except Exception:
            # if the load failed, the remnants should have been
            # cleaned from the load_extension function call
            # so let's load it from our old compiled library.
            lib.setup(self)  # type: ignore
            self.__extensions[name] = lib

            # revert sys.modules back to normal and raise back to caller
            sys.modules.update(modules)
            raise

    @property
    def extensions(self) -> Mapping[str, types.ModuleType]:
        """Mapping[:class:`str`, :class:`py:types.ModuleType`]: 扩展名到扩展的只读映射。"""
        return types.MappingProxyType(self.__extensions)

    # help command stuff

    @property
    def help_command(self) -> Optional[HelpCommand]:
        return self._help_command

    @help_command.setter
    def help_command(self, value: Optional[HelpCommand]) -> None:
        if value is not None:
            if not isinstance(value, HelpCommand):
                raise TypeError('help_command must be a subclass of HelpCommand')
            if self._help_command is not None:
                self._help_command._remove_from_bot(self)
            self._help_command = value
            value._add_to_bot(self)
        elif self._help_command is not None:
            self._help_command._remove_from_bot(self)
            self._help_command = None
        else:
            self._help_command = None

    # command processing

    async def get_prefix(self, message: Message) -> Union[List[str], str]:
        """|coro|

        检索机器人正在监听的前缀，并将消息作为 context。

        Parameters
        -----------
        message: :class:`qq.Message`
            要获取前缀的 context 。

        Returns
        --------
        Union[List[:class:`str`], :class:`str`]
            机器人正在监听的前缀列表或单个前缀。
        """
        prefix = ret = self.command_prefix
        if callable(prefix):
            ret = await qq.utils.maybe_coroutine(prefix, self, message)

        if not isinstance(ret, str):
            try:
                ret = list(ret)
            except TypeError:
                # It's possible that a generator raised this exception.  Don't
                # replace it with our own error if that's the case.
                if isinstance(ret, collections.abc.Iterable):
                    raise

                raise TypeError("command_prefix must be plain string, iterable of strings, or callable "
                                f"returning either of these, not {ret.__class__.__name__}")

            if not ret:
                raise ValueError("Iterable command_prefix must contain at least one prefix")

        return ret

    async def get_context(self, message: Message, *, cls: Type[CXT] = Context) -> CXT:
        r"""|coro|

        从消息中返回调用context。

        这是 :meth:`.process_commands` 的一个更底层的对应部分，允许用户对处理进行更细度的控制。

        返回的 context 不能保证是有效的 调用context，必须检查 :attr:`.Context.valid` 以确保它是有效的。
        如果 context 无效，则它不会在 :meth:`~.Bot.invoke` 下调用。

        Parameters
        -----------
        message: :class:`qq.Message`
            从中获取调用 context 的消息。
        cls
            将用于创建 context 的工厂类。默认情况下，这是 :class:`.Context`。
            如果提供自定义类，它必须与 :class:`.Context`\ 的接口足够相似。

        Returns
        --------
        :class:`.Context`
            调用 context 。 这个类型可以通过 ``cls`` 参数改变。
        """

        view = StringView(message.content)
        ctx = cls(prefix=None, view=view, bot=self, message=message)

        if message.author.id == self.user.id:  # type: ignore
            return ctx

        prefix = await self.get_prefix(message)
        invoked_prefix = prefix

        if isinstance(prefix, str):
            if not view.skip_string(prefix):
                return ctx
        else:
            try:
                # if the context class' __init__ consumes something from the view this
                # will be wrong.  That seems unreasonable though.
                if message.content.startswith(tuple(prefix)):
                    invoked_prefix = qq.utils.find(view.skip_string, prefix)
                else:
                    return ctx

            except TypeError:
                if not isinstance(prefix, list):
                    raise TypeError("get_prefix 必须返回字符串或字符串列表，"
                                    f"而不是 {prefix.__class__.__name__}")

                # It's possible a bad command_prefix got us here.
                for value in prefix:
                    if not isinstance(value, str):
                        raise TypeError("从 get_prefix 返回的可迭代 command_prefix 或列表必须只包含字符串，"
                                        f"而不是 {value.__class__.__name__}")

                # Getting here shouldn't happen
                raise

        if self.strip_after_prefix:
            view.skip_ws()

        invoker = view.get_word()
        ctx.invoked_with = invoker
        # type-checker fails to narrow invoked_prefix type.
        ctx.prefix = invoked_prefix  # type: ignore
        ctx.command = self.all_commands.get(invoker)
        return ctx

    async def invoke(self, ctx: Context) -> None:
        """|coro|

        调用在调用 context 下给出的命令并处理所有内部事件调度机制。

        Parameters
        -----------
        ctx: :class:`.Context`
            要调用的调用 context 。
        """
        if ctx.command is not None:
            self.dispatch('command', ctx)
            try:
                if await self.can_run(ctx, call_once=True):
                    await ctx.command.invoke(ctx)
                else:
                    raise errors.CheckFailure('The global check once functions failed.')
            except errors.CommandError as exc:
                await ctx.command.dispatch_error(ctx, exc)
            else:
                self.dispatch('command_completion', ctx)
        elif ctx.invoked_with:
            exc = errors.CommandNotFound(f'Command "{ctx.invoked_with}" is not found')
            self.dispatch('command_error', ctx, exc)

    async def process_commands(self, message: Message) -> None:
        """|coro|

        函数处理已注册到机器人和其他组的命令。 如果没有这个协程，将不会触发任何命令。

        默认情况下，这个协程在 :func:`.on_message` 事件中被调用。
        如果你选择覆盖 :func:`.on_message` 事件，那么你也应该调用这个协程。

        这是使用其他低级工具构建的，
        相当于调用 :meth:`~.Bot.get_context` 然后调用 :meth:`~.Bot.invoke`。

        这还会检查消息的作者是否是机器人，如果是，则不会调用 :meth:`~.Bot.get_context` 或 :meth:`~.Bot.invoke`。

        Parameters
        -----------
        message: :class:`qq.Message`
            要为其处理命令的消息。
        """
        if message.author.bot:
            return

        ctx = await self.get_context(message)
        await self.invoke(ctx)

    async def on_message(self, message):
        await self.process_commands(message)


class Bot(BotBase, qq.Client):
    """代表一个qq机器人。

    这个类是 :class:`qq.Client` 的子类，因此你可以用这个机器人做任何你可以 :class:`qq.Client` 用做的事情。

    该类还继承了 :class:`.GroupMixin` 以提供管理命令的功能。

    Attributes
    -----------
    command_prefix
        命令前缀是消息内容最初必须包含的内容才能调用命令。
        这个前缀可以是一个字符串来指示前缀应该是什么，
        或者是一个可调用的，它接受机器人作为它的第一个参数和 :class:`qq.Message` 作为它的第二个参数并返回前缀。
        这是为了方便“动态`` 命令前缀。 这个可调用对象可以是常规函数或协程。

        空字符串作为前缀将始终匹配，启用无前缀命令调用。
        虽然这在私聊中可能很有用，但在服务器中应该避免，因为它可能会导致性能问题和意外的命令调用。

        命令前缀也可以是一个可迭代的字符串，表示应该对前缀进行多次检查，第一个匹配的将是调用前缀。
        你可以通过 :attr:`.Context.prefix` 得到这个前缀。 为避免混淆，不允许使用空的可迭代对象。

        .. note::

            传递多个前缀时，请注意不要传递与序列中后面出现的较长前缀相匹配的前缀。
            例如，如果命令前缀是 ``('!', '!?')`` ``'!?'`` 前缀将永远不会与任何消息匹配，因为前一个匹配 ``!`` 是后一个的子集 。
            这在传递空字符串时尤其重要，它应该始终放在最后，因为在匹配之后没有前缀能够被匹配。

    case_insensitive: :class:`bool`
        命令是否应该不区分大小写。 默认为 ``False`` 。 此属性不会延续到组。 如果你还要求组命令不区分大小写，则必须将其设置为每个组。
    description: :class:`str`
        默认帮助消息中带有前缀的内容。
    help_command: Optional[:class:`.HelpCommand`]
        要使用的帮助命令实现。
        这可以在运行时动态设置。 删除帮助命令传递 ``None`` 。
        有关实现帮助命令的更多信息，请参阅 :ref:`ext_commands_help_command`。
    owner_id: Optional[:class:`int`]
        拥有机器人的用户 ID。 必须设置 ``owner_id`` 或 ``owner_ids`` 其中一个
    owner_ids: Optional[Collection[:class:`int`]]
        拥有机器人的多个用户 ID。 这类似于 :attr:`owner_id`。
        出于性能原因，建议使用 :class:`set`。 必须设置 ``owner_id`` 或 ``owner_ids`` 其中一个
    strip_after_prefix: :class:`bool`
        遇到命令前缀后是否去除空白字符。 这允许 ``!   hello`` 和 ``!hello`` 都生效，默认为 ''False'' 。
    """
    pass


class AutoShardedBot(BotBase, qq.AutoShardedClient):
    """除了它是从 :class:`qq.AutoShardedClient` 继承的，其他与 :class:`.Bot` 类似。
    """
    pass
