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

import copy
import functools
import itertools
import re
from typing import Optional, TYPE_CHECKING

import qq.utils
from .core import Group, Command
from .errors import CommandError

if TYPE_CHECKING:
    from .context import Context

__all__ = (
    'Paginator',
    'HelpCommand',
    'DefaultHelpCommand',
    'MinimalHelpCommand',
)


# help -> 在顶部显示机器人的信息并列出子命令
# help 命令 -> 显示命令的详细信息
# help 命令 <子命令链> -> 同上

# <描述>

# <带别名的命令签名>

# <长文档>

# 齿轮:
#   <命令> <简文档>
#   <命令> <简文档>
# 其他齿轮:
#   <命令> <简文档>
# 无类别:
#   <命令> <简文档>

# 键入 <前缀>help 命令以获取有关命令的更多信息。
# 你还可以键入 <前缀>help 类别 以获取有关类别的更多信息。


class Paginator:
    """一个有助于为 qq 消息分页代码块的类。

    .. container:: operations

        .. describe:: len(x)

            返回分页器中的字符总数。

    Attributes
    -----------
    prefix: :class:`str`
        插入到每个页面的前缀。 例如 三个反引号。
    suffix: :class:`str`
        后缀附加在每一页的末尾。 例如 三个反引号。
    max_size: :class:`int`
        页面中允许的最大代码点数。
    linesep: :class:`str`
        行间插入的字符串。 例如 换行符。
    """

    def __init__(self, prefix='', suffix='', max_size=2000, linesep='\n'):
        self.prefix = prefix
        self.suffix = suffix
        self.max_size = max_size
        self.linesep = linesep
        self.clear()

    def clear(self):
        """清除分页器以使其没有页面。"""
        if self.prefix is not None:
            self._current_page = [self.prefix]
            self._count = len(self.prefix) + self._linesep_len  # prefix + newline
        else:
            self._current_page = []
            self._count = 0
        self._pages = []

    @property
    def _prefix_len(self):
        return len(self.prefix) if self.prefix else 0

    @property
    def _suffix_len(self):
        return len(self.suffix) if self.suffix else 0

    @property
    def _linesep_len(self):
        return len(self.linesep)

    def add_line(self, line='', *, empty=False):
        """向当前页面添加一行。

        如果该行超过 :attr:`max_size`，则会引发异常。

        Parameters
        -----------
        line: :class:`str`
            要添加的行。
        empty: :class:`bool`
            指示是否应添加另一个空行。

        Raises
        ------
        RuntimeError
            该行对于当前的 :attr:`max_size` 来说太大了。
        """
        max_page_size = self.max_size - self._prefix_len - self._suffix_len - 2 * self._linesep_len
        if len(line) > max_page_size:
            raise RuntimeError(f'行超过最大页面大小 {max_page_size}')

        if self._count + len(line) + self._linesep_len > self.max_size - self._suffix_len:
            self.close_page()

        self._count += len(line) + self._linesep_len
        self._current_page.append(line)

        if empty:
            self._current_page.append('')
            self._count += self._linesep_len

    def close_page(self):
        """提前终止页面。"""
        if self.suffix is not None:
            self._current_page.append(self.suffix)
        self._pages.append(self.linesep.join(self._current_page))

        if self.prefix is not None:
            self._current_page = [self.prefix]
            self._count = len(self.prefix) + self._linesep_len  # prefix + linesep
        else:
            self._current_page = []
            self._count = 0

    def __len__(self):
        total = sum(len(p) for p in self._pages)
        return total + self._count

    @property
    def pages(self):
        """List[:class:`str`]: 返回呈现的页面列表。"""
        # we have more than just the prefix in our current page
        if len(self._current_page) > (0 if self.prefix is None else 1):
            self.close_page()
        return self._pages

    def __repr__(self):
        fmt = '<Paginator prefix: {0.prefix!r} suffix: {0.suffix!r} linesep: {0.linesep!r} max_size: {0.max_size} ' \
              'count: {0._count}> '
        return fmt.format(self)


def _not_overriden(f):
    f.__help_command_not_overriden__ = True
    return f


class _HelpCommandImpl(Command):
    def __init__(self, inject, *args, **kwargs):
        super().__init__(inject.command_callback, *args, **kwargs)
        self._original = inject
        self._injected = inject

    async def prepare(self, ctx):
        self._injected = injected = self._original.copy()
        injected.context = ctx
        self.callback = injected.command_callback

        on_error = injected.on_help_command_error
        if not hasattr(on_error, '__help_command_not_overriden__'):
            if self.cog is not None:
                self.on_error = self._on_error_cog_implementation
            else:
                self.on_error = on_error

        await super().prepare(ctx)

    async def _parse_arguments(self, ctx):
        # Make the parser think we don't have a cog so it doesn't
        # inject the parameter into `ctx.args`.
        original_cog = self.cog
        self.cog = None
        try:
            await super()._parse_arguments(ctx)
        finally:
            self.cog = original_cog

    async def _on_error_cog_implementation(self, dummy, ctx, error):
        await self._injected.on_help_command_error(ctx, error)

    @property
    def clean_params(self):
        result = self.params.copy()
        try:
            del result[next(iter(result))]
        except StopIteration:
            raise ValueError('缺少 context 参数') from None
        else:
            return result

    def _inject_into_cog(self, cog):
        # Warning: hacky

        # Make the cog think that get_commands returns this command
        # as well if we inject it without modifying __cog_commands__
        # since that's used for the injection and ejection of cogs.
        def wrapped_get_commands(*, _original=cog.get_commands):
            ret = _original()
            ret.append(self)
            return ret

        # Ditto here
        def wrapped_walk_commands(*, _original=cog.walk_commands):
            yield from _original()
            yield self

        functools.update_wrapper(wrapped_get_commands, cog.get_commands)
        functools.update_wrapper(wrapped_walk_commands, cog.walk_commands)
        cog.get_commands = wrapped_get_commands
        cog.walk_commands = wrapped_walk_commands
        self.cog = cog

    def _eject_cog(self):
        if self.cog is None:
            return

        # revert back into their original methods
        cog = self.cog
        cog.get_commands = cog.get_commands.__wrapped__
        cog.walk_commands = cog.walk_commands.__wrapped__
        self.cog = None


class HelpCommand:
    r"""帮助命令格式的基本实现。

    .. note::

        每次调用命令本身时，都会在内部深度复制此类的实例，

        这意味着在命令调用之间依赖于此类的状态相同将不会按预期工作。

    Attributes
    ------------
    context: Optional[:class:`Context`]
        调用此帮助格式化程序的 context 。 这通常在分配的帮助命令 :func:`command_callback`\ 被调用后设置。
    show_hidden: :class:`bool`
        指定是否应在输出中显示隐藏命令。
        默认为 ``False`` 。
    verify_checks: Optional[:class:`bool`]
        指定命令是否应该调用和验证它们的 :attr:`.Command.checks`。 如果 ``True``，则总是调用 :attr:`.Command.checks`。
        如果 ``None`` ，则仅在公会设置中调用 :attr:`.Command.checks`。 如果 ``False``，则从不调用 :attr:`.Command.checks`。
        默认为 ``True`` 。

    command_attrs: :class:`dict`
        用于构建帮助命令的选项字典。
        这允许你在不实际更改命令的实现的情况下更改命令行为。
        这些属性将与传入 :class:`.Command` 构造函数的属性相同。
    """

    MENTION_TRANSFORMS = {
        '@everyone': '@\u200beveryone',
        r'<@!?[0-9]{17,22}>': '@deleted-user',
        r'<@&[0-9]{17,22}>': '@deleted-role',
    }

    MENTION_PATTERN = re.compile('|'.join(MENTION_TRANSFORMS.keys()))

    def __new__(cls, *args, **kwargs):
        # To prevent race conditions of a single instance while also allowing
        # for settings to be passed the original arguments passed must be assigned
        # to allow for easier copies (which will be made when the help command is actually called)
        # see issue 2123
        self = super().__new__(cls)

        # Shallow copies cannot be used in this case since it is not unusual to pass
        # instances that need state, e.g. Paginator or what have you into the function
        # The keys can be safely copied as-is since they're 99.99% certain of being
        # string keys
        deepcopy = copy.deepcopy
        self.__original_kwargs__ = {k: deepcopy(v) for k, v in kwargs.items()}
        self.__original_args__ = deepcopy(args)
        return self

    def __init__(self, **options):
        self.show_hidden = options.pop('show_hidden', False)
        self.verify_checks = options.pop('verify_checks', True)
        self.command_attrs = attrs = options.pop('command_attrs', {})
        attrs.setdefault('name', 'help')
        attrs.setdefault('help', '显示此消息')
        self.context: Context = qq.utils.MISSING
        self._command_impl = _HelpCommandImpl(self, **self.command_attrs)

    def copy(self):
        obj = self.__class__(*self.__original_args__, **self.__original_kwargs__)
        obj._command_impl = self._command_impl
        return obj

    def _add_to_bot(self, bot):
        command = _HelpCommandImpl(self, **self.command_attrs)
        bot.add_command(command)
        self._command_impl = command

    def _remove_from_bot(self, bot):
        bot.remove_command(self._command_impl.name)
        self._command_impl._eject_cog()

    def add_check(self, func):
        """向帮助命令添加检查。

        Parameters
        ----------
        func
            将用作检查的函数。
        """

        self._command_impl.add_check(func)

    def remove_check(self, func):
        """
        从帮助命令中删除检查。

        此函数是幂等的，如果该函数不在命令的检查中，则不会引发异常。

        Parameters
        ----------
        func
            要从检查中删除的函数。
        """

        self._command_impl.remove_check(func)

    def get_bot_mapping(self):
        """检索传递给 :meth:`send_bot_help` 的机器人映射。"""
        bot = self.context.bot
        mapping = {cog: cog.get_commands() for cog in bot.cogs.values()}
        mapping[None] = [c for c in bot.commands if c.cog is None]
        return mapping

    @property
    def invoked_with(self):
        """与 :attr:`Context.invoked_with` 类似，但是正确处理使用 :meth:`Context.send_help` 的情况。

        如果经常使用帮助命令，则返回 :attr:`Context.invoked_with` 属性。
        否则，如果使用 :meth:`Context.send_help` 调用了帮助命令，则它返回帮助命令的内部命令名称。

        Returns
        ---------
        :class:`str`
            触发此调用的命令名称。
        """
        command_name = self._command_impl.name
        ctx = self.context
        if ctx is None or ctx.command is None or ctx.command.qualified_name != command_name:
            return command_name
        return ctx.invoked_with

    def get_command_signature(self, command):
        """检索帮助页面的签名部分。

        Parameters
        ------------
        command: :class:`Command`
            获取签名的命令。

        Returns
        --------
        :class:`str`
            命令的签名。
        """

        parent = command.parent
        entries = []
        while parent is not None:
            if not parent.signature or parent.invoke_without_command:
                entries.append(parent.name)
            else:
                entries.append(parent.name + ' ' + parent.signature)
            parent = parent.parent
        parent_sig = ' '.join(reversed(entries))

        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = f'[{command.name}|{aliases}]'
            if parent_sig:
                fmt = parent_sig + ' ' + fmt
            alias = fmt
        else:
            alias = command.name if not parent_sig else parent_sig + ' ' + command.name

        return f'{self.context.clean_prefix}{alias} {command.signature}'

    def remove_mentions(self, string):
        """从字符串中删除提及以防止滥用。

        这包括 “@所有人”、成员提及和身份组提及。

        Returns
        -------
        :class:`str`
            删除了提及的字符串。
        """

        def replace(obj, *, transforms=self.MENTION_TRANSFORMS):
            return transforms.get(obj.group(0), '@invalid')

        return self.MENTION_PATTERN.sub(replace, string)

    @property
    def cog(self):
        """用于检索或设置帮助命令的齿轮的属性。

        当为 help 命令设置一个齿轮时，就好像 help 命令属于该齿轮。所有齿轮特殊方法都将应用于 help 命令，并且会在卸载时自动取消设置。

        要从帮助命令中取消绑定齿轮，你可以将其设置为 ``None``。

        Returns
        --------
        Optional[:class:`Cog`]
            当前为 help 命令设置的齿轮。
        """
        return self._command_impl.cog

    @cog.setter
    def cog(self, cog):
        # Remove whatever cog is currently valid, if any
        self._command_impl._eject_cog()

        # If a new cog is set then inject it.
        if cog is not None:
            self._command_impl._inject_into_cog(cog)

    def command_not_found(self, string):
        """|maybecoro|

        在帮助命令中找不到命令时调用的方法。这对于 i18n 很有用。

        默认为 ``未找到名为 {0} 的命令。``

        Parameters
        ------------
        string: :class:`str`
            包含无效命令的字符串。请注意，这已被删除以防止滥用。

        Returns
        ---------
        :class:`str`
            未找到命令时使用的字符串。
        """
        return f'未找到名为“{string}”的命令。'

    def subcommand_not_found(self, command, string):
        """|maybecoro|

        当命令没有在帮助命令中请求的子命令时调用的方法。这对于 i18n 很有用。

        Defaults to either:

        - ``'命令“{command.qualified_name}”没有子命令。'``
            - 如果 ``command`` 参数中没有子命令。
        - ``'命令“{command.qualified_name}”没有名为 {string} 的子命令'``
            - 如果 ``command`` 参数有子命令，但没有名为 ``string`` 的子命令。

        Parameters
        ------------
        command: :class:`Command`
            没有请求子命令的命令。
        string: :class:`str`
            包含无效子命令的字符串。请注意，这已被删除以防止滥用。

        Returns
        ---------
        :class:`str`
            当命令没有请求子命令时使用的字符串。
        """
        if isinstance(command, Group) and len(command.all_commands) > 0:
            return f'命令“{command.qualified_name}”没有名为 {string} 的子命令'
        return f'命令“{command.qualified_name}”没有子命令。'

    async def filter_commands(self, commands, *, sort=False, key=None):
        """|coro|

        返回过滤后的命令列表并可选择对它们进行排序。

        这考虑了 :attr:`verify_checks` 和 :attr:`show_hidden` 属性。

        Parameters
        ------------
        commands: Iterable[:class:`Command`]
            被过滤的命令的迭代。
        sort: :class:`bool`
            是否对结果进行排序。
        key: Optional[Callable[:class:`Command`, Any]]
            传递给 :func:`py:sorted` 的可选键函数，它以 :class:`Command` 作为其唯一参数。
            如果 ``sort`` 作为 ``True`` 传递，那么这将默认为命令名称。

        Returns
        ---------
        List[:class:`Command`]
            通过过滤器的命令列表。
        """

        if sort and key is None:
            key = lambda c: c.name

        iterator = commands if self.show_hidden else filter(lambda c: not c.hidden, commands)

        if self.verify_checks is False:
            # if we do not need to verify the checks then we can just
            # run it straight through normally without using await.
            return sorted(iterator, key=key) if sort else list(iterator)

        if self.verify_checks is None and not self.context.guild:
            # if verify_checks is None and we're in a DM, don't verify
            return sorted(iterator, key=key) if sort else list(iterator)

        # if we're here then we need to check every command if it can run
        async def predicate(cmd):
            try:
                return await cmd.can_run(self.context)
            except CommandError:
                return False

        ret = []
        for cmd in iterator:
            valid = await predicate(cmd)
            if valid:
                ret.append(cmd)

        if sort:
            ret.sort(key=key)
        return ret

    def get_max_size(self, commands):
        """返回指定命令列表的最大名称长度。

        Parameters
        ------------
        commands: Sequence[:class:`Command`]
            检查最大尺寸的一系列命令。

        Returns
        --------
        :class:`int`
            命令的最大宽度。
        """

        as_lengths = (qq.utils._string_width(c.name) for c in commands)
        return max(as_lengths, default=0)

    def get_destination(self):
        """返回 :class:`~qq.abc.Messageable` 将在其中输出帮助命令。

        你可以覆盖此方法以自定义行为。

        默认情况下，这将返回 context 的子频道。

        Returns
        -------
        :class:`.abc.Messageable`
            将输出帮助命令的目的地。
        """
        return self.context.channel

    async def send_error_message(self, error):
        """|coro|

        在帮助命令中发生错误时处理实现。例如 :meth:`command_not_found` 的结果会被传递到这里。

        你可以覆盖此方法以自定义行为。

        默认情况下，这会将错误消息发送到 :meth:`get_destination` 指定的目的地。

        .. note::

            你可以使用 :attr:`HelpCommand.context` 访问调用 context 。

        Parameters
        ------------
        error: :class:`str`
            要向用户显示的错误消息。请注意，这已被删除以防止滥用。
        """
        destination = self.get_destination()
        await destination.send(error)

    @_not_overriden
    async def on_help_command_error(self, ctx, error):
        """|coro|

        帮助命令的错误处理程序，由 :ref:`ext_commands_error_handler` 指定。

        如果在调用错误处理程序时需要某些特定行为，则可用于覆盖。

        默认情况下，此方法不执行任何操作，只会传播到默认错误处理程序。

        Parameters
        ------------
        ctx: :class:`Context`
            调用 context 。
        error: :class:`CommandError`
            引发的错误。
        """
        pass

    async def send_bot_help(self, mapping):
        """|coro|

        处理帮助命令中 bot 命令页面的实现。当不带参数调用帮助命令时调用此函数。

        应该注意的是，这个方法不返回任何东西——而是应该在这个方法内部完成实际的消息发送。
        行为良好的子类应该使用 :meth:`get_destination` 来知道发送到哪里，因为这是其他用户的自定义点。

        你可以覆盖此方法以自定义行为。

        .. note::

            你可以使用 :attr:`HelpCommand.context` 访问调用 context 。

            此外，映射中的命令不会被过滤。要进行过滤，你必须自己调用 :meth:`filter_commands`。

        Parameters
        ------------
        mapping: Mapping[Optional[:class:`Cog`], List[:class:`Command`]]
            齿轮到用户请求帮助的命令的映射。映射的键是命令所属的 :class:`~.commands.Cog`，
            如果没有，则为 ``None`` ，值是属于该齿轮的命令列表.
        """
        return None

    async def send_cog_help(self, cog):
        """|coro|

        处理帮助命令中齿轮页面的实现。当使用齿轮作为参数调用 ``help`` 命令时，将调用此函数。

        应该注意的是，这个方法不返回任何东西——而是应该在这个方法内部完成实际的消息发送。
        行为良好的子类应该使用 :meth:`get_destination` 来知道发送到哪里，因为这是其他用户的自定义点。

        你可以覆盖此方法以自定义行为。

        .. note::

            你可以使用 :attr:`HelpCommand.context` 访问调用 context 。

            要获取属于该齿轮的命令，请参见  :meth:`Cog.get_commands` 。
            返回的命令未过滤。要进行过滤，你必须自己调用 :meth:`filter_commands`。

        Parameters
        -----------
        cog: :class:`Cog`
            被请求帮助的齿轮。
        """
        return None

    async def send_group_help(self, group):
        """|coro|

        处理帮助命令中组页面的实现。
        当使用组作为参数调用帮助命令时，将调用此函数。

        应该注意的是，这个方法不返回任何东西——而是应该在这个方法内部完成实际的消息发送。
        行为良好的子类应该使用 :meth:`get_destination` 来知道发送到哪里，因为这是其他用户的自定义点。

        你可以覆盖此方法以自定义行为。

        .. note::

            你可以使用 :attr:`HelpCommand.context` 访问调用 context 。

            要获取不带别名的属于该组的命令，请参阅 :attr:`Group.commands`。
            返回的命令未过滤。要进行过滤，你必须自己调用 :meth:`filter_commands`。

        Parameters
        -----------
        group: :class:`Group`
            被请求帮助的组。
        """
        return None

    async def send_command_help(self, command):
        """|coro|

        处理帮助命令中单个命令页面的实现。

        应该注意的是，这个方法不返回任何东西——而是应该在这个方法内部完成实际的消息发送。
        行为良好的子类应该使用 :meth:`get_destination` 来知道发送到哪里，因为这是其他用户的自定义点。

        你可以覆盖此方法以自定义行为。

        .. note::

            你可以使用 :attr:`HelpCommand.context` 访问调用 context 。

        .. admonition:: 显示帮助
            :class: helpful

            某些属性和方法有助于帮助命令显示，例如：

            - :attr:`Command.help`
            - :attr:`Command.brief`
            - :attr:`Command.short_doc`
            - :attr:`Command.description`
            - :meth:`get_command_signature`

            不是只有是这些属性，但你可以从随意使用这些属性开始来帮助你开始获得所需的输出。

        Parameters
        -----------
        command: :class:`Command`
            请求帮助的命令。
        """
        return None

    async def prepare_help_command(self, ctx, command=None):
        """|coro|

        一种低级方法，可用于在执行任何操作之前准备帮助命令。
        例如，如果你需要在命令进行处理之前在子类中准备一些状态，那么这将是执行此操作的地方。

        默认实现什么都不做。

        .. note::

            这在帮助命令回调主体 **内** 调用。因此，内部发生的所有常见规则也适用于此。

        Parameters
        -----------
        ctx: :class:`Context`
            调用 context 。
        command: Optional[:class:`str`]
            传递给 help 命令的参数。
        """
        pass

    async def command_callback(self, ctx, *, command=None):
        """|coro|

        help 命令的实际执行。

        不建议覆盖此方法，而是通过实际调度的方法更改行为。

        - :meth:`send_bot_help`
        - :meth:`send_cog_help`
        - :meth:`send_group_help`
        - :meth:`send_command_help`
        - :meth:`get_destination`
        - :meth:`command_not_found`
        - :meth:`subcommand_not_found`
        - :meth:`send_error_message`
        - :meth:`on_help_command_error`
        - :meth:`prepare_help_command`
        """
        await self.prepare_help_command(ctx, command)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        # Check if it's a cog
        cog = bot.get_cog(command)
        if cog is not None:
            return await self.send_cog_help(cog)

        maybe_coro = qq.utils.maybe_coroutine

        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        keys = command.split(' ')
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)


class DefaultHelpCommand(HelpCommand):
    """默认帮助命令的执行。

    这继承自 :class:`HelpCommand` 。

    它使用以下属性对其进行了扩展。

    Attributes
    ------------
    width: :class:`int`
        适合一行的最大字符数。默认为 80。
    sort_commands: :class:`bool`
        是否按字母顺序对输出中的命令进行排序。默认为“真”。
    dm_help: Optional[:class:`bool`]
        一个三个选择参数，指示帮助命令是否应该私聊用户而不是将其发送到它接收它的频道。
        如果布尔值设置为 ``True`` ，则所有帮助输出都是私聊的。
        如果 ``False`` ，则没有任何帮助输出是私聊。
        如果 ``None`` ，那么当帮助消息变得太长（由超过 :attr:`dm_help_threshold` 字符决定）时，机器人只会发送私聊。
        默认为 ``False`` 。
    dm_help_threshold: Optional[:class:`int`]
        如果 :attr:`dm_help` 设置为 ``None`` ，则分页器在将私聊发送给用户之前必须累积的字符数。默认为 ``1000`` 。
    indent: :class:`int`
        从标题中缩进命令的程度。默认为 ``2`` 。
    commands_heading: :class:`str`
        当使用类别名称调用帮助命令时使用的命令列表的标题字符串。对 i18n 有用。默认为 ``"命令："``
    no_category: :class:`str`
        存在不属于任何类别（cog）的命令时使用的字符串。对 i18n 有用。默认为 ``"无类别" ``
    paginator: :class:`Paginator`
        用于对帮助命令输出进行分页的分页器。
    """

    def __init__(self, **options):
        self.width = options.pop('width', 80)
        self.indent = options.pop('indent', 2)
        self.sort_commands = options.pop('sort_commands', True)
        self.dm_help = options.pop('dm_help', False)
        self.dm_help_threshold = options.pop('dm_help_threshold', 1000)
        self.commands_heading = options.pop('commands_heading', "命令：")
        self.no_category = options.pop('no_category', '无类别')
        self.paginator = options.pop('paginator', None)

        if self.paginator is None:
            self.paginator = Paginator()

        super().__init__(**options)

    def shorten_text(self, text):
        """:class:`str`: 缩短文本以适应 :attr:`width`。"""
        if len(text) > self.width:
            return text[:self.width - 3].rstrip() + '...'
        return text

    def get_ending_note(self):
        """:class:`str`: 返回帮助命令的结束注释。这主要用于覆盖 i18n 目的。"""
        command_name = self.invoked_with
        return (
            f"输入 {self.context.clean_prefix}{command_name} 命令 以获取有关命令的更多信息。\n"
            f"你还可以输入 {self.context.clean_prefix}{command_name} 类别 以获取有关类别的更多信息。"
        )

    def add_indented_commands(self, commands, *, heading, max_size=None):
        """在指定标题后缩进命令列表。

        格式添加到 :attr:`paginator`。

        默认实现是命令名称由 :attr:`indent` 空格缩进，
        填充到 ``max_size`` 后跟命令的 :attr:`Command.short_doc` 然后缩短以适应 :attr:`width`。

        Parameters
        -----------
        commands: Sequence[:class:`Command`]
            用于缩进输出的命令列表。
        heading: :class:`str`
            要添加到输出的标题。仅当命令列表大于 0 时才添加此项。
        max_size: Optional[:class:`int`]
            用于缩进间隙的最大尺寸。如果未指定，则在命令参数上调用 :meth:`~HelpCommand.get_max_size`。
        """

        if not commands:
            return

        self.paginator.add_line(heading)
        max_size = max_size or self.get_max_size(commands)

        get_width = qq.utils._string_width
        for command in commands:
            name = command.name
            width = max_size - (get_width(name) - len(name))
            entry = f'{self.indent * " "}{name:<{width}} {command.short_doc}'
            self.paginator.add_line(self.shorten_text(entry))

    async def send_pages(self):
        """将页面输出从 :attr:`paginator` 发送到目的地的辅助实用程序。"""
        destination = self.get_destination()
        for page in self.paginator.pages:
            await destination.send(page)

    def add_command_formatting(self, command):
        """用于格式化命令和组的非缩进块的实用函数。

        Parameters
        ------------
        command: :class:`Command`
            要格式化的命令。
        """

        if command.description:
            self.paginator.add_line(command.description, empty=True)

        signature = self.get_command_signature(command)
        self.paginator.add_line(signature, empty=True)

        if command.help:
            try:
                self.paginator.add_line(command.help, empty=True)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.paginator.add_line(line)
                self.paginator.add_line()

    def get_destination(self):
        ctx = self.context
        if self.dm_help is True:
            return ctx.author
        elif self.dm_help is None and len(self.paginator) > self.dm_help_threshold:
            return ctx.author
        else:
            return ctx.channel

    async def prepare_help_command(self, ctx, command):
        self.paginator.clear()
        await super().prepare_help_command(ctx, command)

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        if bot.description:
            # <description> portion
            self.paginator.add_line(bot.description, empty=True)

        no_category = f'\u200b{self.no_category}:'

        def get_category(command, *, no_category=no_category):
            cog = command.cog
            return cog.qualified_name + ':' if cog is not None else no_category

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        max_size = self.get_max_size(filtered)
        to_iterate = itertools.groupby(filtered, key=get_category)

        # Now we can add the commands to the page.
        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name) if self.sort_commands else list(commands)
            self.add_indented_commands(commands, heading=category, max_size=max_size)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()

    async def send_command_help(self, command):
        self.add_command_formatting(command)
        self.paginator.close_page()
        await self.send_pages()

    async def send_group_help(self, group):
        self.add_command_formatting(group)

        filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
        self.add_indented_commands(filtered, heading=self.commands_heading)

        if filtered:
            note = self.get_ending_note()
            if note:
                self.paginator.add_line()
                self.paginator.add_line(note)

        await self.send_pages()

    async def send_cog_help(self, cog):
        if cog.description:
            self.paginator.add_line(cog.description, empty=True)

        filtered = await self.filter_commands(cog.get_commands(), sort=self.sort_commands)
        self.add_indented_commands(filtered, heading=self.commands_heading)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()


class MinimalHelpCommand(HelpCommand):
    """具有最少输出的帮助命令的实现。

    这继承自 :class:`HelpCommand`。

    Attributes
    ------------
    sort_commands: :class:`bool`
        是否按字母顺序对输出中的命令进行排序。默认为 ``True`` 。
    commands_heading: :class:`str`
        当使用类别名称调用帮助命令时使用的命令列表的标题字符串。对 i18n 有用。默认为 ``“命令”`` 。
    aliases_heading: :class:`str`
        别名列表的标题字符串用于列出命令的别名。对 i18n 有用。默认为``"别名："`` 。
    dm_help: Optional[:class:`bool`]
        一个三个选择参数，指示帮助命令是否应该私聊用户而不是将其发送到它接收它的频道。
        如果布尔值设置为 ``True`` ，则所有帮助输出都是私聊的。
        如果 ``False`` ，则没有任何帮助输出是私聊。
        如果 ``None`` ，那么当帮助消息变得太长（由超过 :attr:`dm_help_threshold` 字符决定）时，机器人只会发送私聊。
        默认为 ``False`` 。
    dm_help_threshold: Optional[:class:`int`]
        如果 :attr:`dm_help` 设置为 ``None`` ，则分页器在将私聊发送给用户之前必须累积的字符数。默认为 ``1000`` 。
    no_category: :class:`str`
        存在不属于任何类别（cog）的命令时使用的字符串。对 i18n 有用。默认为 ``"无类别:" ``
    paginator: :class:`Paginator`
        用于对帮助命令输出进行分页的分页器。
    """

    def __init__(self, **options):
        self.sort_commands = options.pop('sort_commands', True)
        self.commands_heading = options.pop('commands_heading', "命令")
        self.dm_help = options.pop('dm_help', False)
        self.dm_help_threshold = options.pop('dm_help_threshold', 1000)
        self.aliases_heading = options.pop('aliases_heading', "别名：")
        self.no_category = options.pop('no_category', '无类别')
        self.paginator = options.pop('paginator', None)

        if self.paginator is None:
            self.paginator = Paginator(suffix=None, prefix=None)

        super().__init__(**options)

    async def send_pages(self):
        """将页面输出从 :attr:`paginator` 发送到目的地的辅助实用程序。"""
        destination = self.get_destination()
        for page in self.paginator.pages:
            await destination.send(page)

    def get_opening_note(self):
        """返回帮助命令的开头注释。这主要用于覆盖 i18n 目的。

        默认实现返回 ::

            使用 `{prefix}{command_name} [命令]` 获取有关命令的更多信息。
            你还可以使用 `{prefix}{command_name} [类别]` 获取有关类别的更多信息。

        Returns
        -------
        :class:`str`
            The help command opening note.
        """
        command_name = self.invoked_with
        return (
            f"使用 `{self.context.clean_prefix}{command_name} [命令]` 获取有关命令的更多信息。\n"
            f"你还可以使用 `{self.context.clean_prefix}{command_name} [类别]` 获取有关类别的更多信息。"
        )

    def get_command_signature(self, command):
        return f'{self.context.clean_prefix}{command.qualified_name} {command.signature}'

    def get_ending_note(self):
        """返回帮助命令的结束注释。这主要用于覆盖 i18n 目的。

        默认实现什么都不做。

        Returns
        -------
        :class:`str`
            帮助命令结束注释。
        """
        return None

    def add_bot_commands_formatting(self, commands, heading):
        """将带有命令的缩小机器人标题添加到输出中。

        格式应该添加到 :attr:`paginator`。

        默认实现是一个标题，下一行是由 EN SPACE (U+2002) 分隔的命令。

        Parameters
        -----------
        commands: Sequence[:class:`Command`]
            属于标题的命令列表。
        heading: :class:`str`
            要添加到行的标题。
        """
        if commands:
            # U+2002 Middle Dot
            joined = '\u2002'.join(c.name for c in commands)
            self.paginator.add_line(f'__**{heading}**__')
            self.paginator.add_line(joined)

    def add_subcommand_formatting(self, command):
        """在子命令上添加格式信息。

        格式应该添加到 :attr:`paginator`。

        默认实现是前缀和:attr:`Command.qualified_name` 可选后跟一个短划线和命令的:attr:`Command.short_doc`。

        Parameters
        -----------
        command: :class:`Command`
            显示信息的命令。
        """
        fmt = '{0}{1} \N{EN DASH} {2}' if command.short_doc else '{0}{1}'
        self.paginator.add_line(fmt.format(self.context.clean_prefix, command.qualified_name, command.short_doc))

    def add_aliases_formatting(self, aliases):
        """添加有关命令别名的格式信息。

        格式应该添加到 :attr:`paginator`。

        默认实现是 :attr:`aliases_heading` 跟逗号分隔的别名列表。

        如果没有要格式化的别名，则不会调用此方法。

        Parameters
        -----------
        aliases: Sequence[:class:`str`]
            要格式化的别名列表。
        """
        self.paginator.add_line(f'**{self.aliases_heading}** {", ".join(aliases)}', empty=True)

    def add_command_formatting(self, command):
        """用于格式化命令和组的实用程序函数。

        Parameters
        ------------
        command: :class:`Command`
            要格式化的命令。
        """

        if command.description:
            self.paginator.add_line(command.description, empty=True)

        signature = self.get_command_signature(command)
        if command.aliases:
            self.paginator.add_line(signature)
            self.add_aliases_formatting(command.aliases)
        else:
            self.paginator.add_line(signature, empty=True)

        if command.help:
            try:
                self.paginator.add_line(command.help, empty=True)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.paginator.add_line(line)
                self.paginator.add_line()

    def get_destination(self):
        ctx = self.context
        if self.dm_help is True:
            return ctx.author
        elif self.dm_help is None and len(self.paginator) > self.dm_help_threshold:
            return ctx.author
        else:
            return ctx.channel

    async def prepare_help_command(self, ctx, command):
        self.paginator.clear()
        await super().prepare_help_command(ctx, command)

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        if bot.description:
            self.paginator.add_line(bot.description, empty=True)

        note = self.get_opening_note()
        if note:
            self.paginator.add_line(note, empty=True)

        no_category = f'\u200b{self.no_category}'

        def get_category(command, *, no_category=no_category):
            cog = command.cog
            return cog.qualified_name if cog is not None else no_category

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name) if self.sort_commands else list(commands)
            self.add_bot_commands_formatting(commands, category)

        note = self.get_ending_note()
        if note:
            self.paginator.add_line()
            self.paginator.add_line(note)

        await self.send_pages()

    async def send_cog_help(self, cog):
        bot = self.context.bot
        if bot.description:
            self.paginator.add_line(bot.description, empty=True)

        note = self.get_opening_note()
        if note:
            self.paginator.add_line(note, empty=True)

        if cog.description:
            self.paginator.add_line(cog.description, empty=True)

        filtered = await self.filter_commands(cog.get_commands(), sort=self.sort_commands)
        if filtered:
            self.paginator.add_line(f'**{cog.qualified_name} {self.commands_heading}**')
            for command in filtered:
                self.add_subcommand_formatting(command)

            note = self.get_ending_note()
            if note:
                self.paginator.add_line()
                self.paginator.add_line(note)

        await self.send_pages()

    async def send_group_help(self, group):
        self.add_command_formatting(group)

        filtered = await self.filter_commands(group.commands, sort=self.sort_commands)
        if filtered:
            note = self.get_opening_note()
            if note:
                self.paginator.add_line(note, empty=True)

            self.paginator.add_line(f'**{self.commands_heading}**')
            for command in filtered:
                self.add_subcommand_formatting(command)

            note = self.get_ending_note()
            if note:
                self.paginator.add_line()
                self.paginator.add_line(note)

        await self.send_pages()

    async def send_command_help(self, command):
        self.add_command_formatting(command)
        self.paginator.close_page()
        await self.send_pages()
