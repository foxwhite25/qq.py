.. currentmodule:: qq

.. _ext_commands_commands:

命令
==========

命令扩展最吸引人的方面之一是定义命令是多么容易，以及你如何可以任意嵌套组和命令以拥有丰富的子命令系统。

命令是通过将其附加到常规 Python 函数来定义的。
然后用户使用与 Python 函数类似的函数调用该命令。

例如，在给定的命令定义中：

.. code-block:: python3

    @bot.command()
    async def foo(ctx, arg):
        await ctx.send(arg)

使用以下前缀（``$``），用户可以通过以下方式调用它：

.. code-block:: none

    $foo abc

命令必须始终至少有一个参数 ``ctx`` ，即 :class:`.Context` 作为第一个参数。

有两种注册命令的方法。 第一个是使用 :meth:`.Bot.command` 装饰器，如上例所示。
第二种是在实例上使用 :func:`~ext.commands.command` 装饰器，
然后是 :meth:`.Bot.add_command`。

本质上，这两个是等价的： ::

    from qq.ext import commands

    bot = commands.Bot(command_prefix='$')

    @bot.command()
    async def test(ctx):
        pass

    # 或者:

    @commands.command()
    async def test(ctx):
        pass

    bot.add_command(test)

由于 :meth:`.Bot.command` 装饰器更短且更容易理解，因此它将是整个文档中使用的范例。

任何被 :class:`.Command` 构造函数接受的参数都可以传递给装饰器。 例如，将名称更改为函数以外的其他名称就像这样做一样简单：

.. code-block:: python3

    @bot.command(name='list')
    async def _list(ctx, arg):
        pass

参数
------------

由于我们通过创建 Python 函数来定义命令，因此我们还通过函数参数定义了参数传递行为。

某些参数类型在用户端做不同的事情，并且支持大多数形式的参数类型。

位置参数
++++++++++++

参数传递的最基本形式是位置参数。 这是我们按原样传递参数的地方：

.. code-block:: python3

    @bot.command()
    async def test(ctx, arg):
        await ctx.send(arg)


在机器人那边，你可以通过传递一个常规字符串来提供位置参数：

.. image:: /images/commands/positional1.png

要使用中间有空格的单词，你应该加上引号：

.. image:: /images/commands/positional2.png

作为警告的说明，如果你省略引号，你将只会得到第一个单词：

.. image:: /images/commands/positional3.png

由于位置参数只是常规的 Python 参数，因此你可以拥有任意数量的参数：

.. code-block:: python3

    @bot.command()
    async def test(ctx, arg1, arg2):
        await ctx.send(f'你传入了 {arg1} 和 {arg2}')

变量
++++++++++

有时你希望用户传入不确定数量的参数。 该库支持这类似于在 Python 中做到变量列表参数的方式:

.. code-block:: python3

    @bot.command()
    async def test(ctx, *args):
        arguments = ', '.join(args)
        await ctx.send(f'{len(args)} 参数：{args}')

这允许我们的用户根据需要接受一个或多个参数。 这类似于位置参数，因此应该引用多字参数。

例如，在机器人那边：

.. image:: /images/commands/variable1.png

如果用户想输入一个多词参数，他们必须像之前一样引用它：

.. image:: /images/commands/variable2.png

请注意，与 Python 函数行为类似，用户在技术上可以根本不传递任何参数：

.. image:: /images/commands/variable3.png

由于 ``args`` 变量是一个 :class:`py:tuple`，你可以做任何你通常可以做的事情。

仅关键字参数
++++++++++++++++++++++++

当你想自己处理参数的解析或不想将多字用户输入包装到引号，你可以要求库将其余部分作为单个参数提供给你。
我们通过使用 **仅关键字参数** 来做到这一点，

见下图：

.. code-block:: python3

    @bot.command()
    async def test(ctx, *, arg):
        await ctx.send(arg)

.. warning::

    由于解析歧义，你只能有一个仅限关键字的参数。

在机器人那边，我们不需要用空格引用输入：

.. image:: /images/commands/keyword1.png

请记住，将它用引号括起来会保持原样：

.. image:: /images/commands/keyword2.png

默认情况下，仅关键字参数被去除空格以使其更易于使用。
这种行为可以通过装饰器中的 :attr:`.Command.rest_is_raw` 参数来切换。

.. _ext_commands_context:

调用 context
-------------------

如前所述，每个命令必须至少接受一个参数，称为 :class:`~ext.commands.Context`。

此参数使你可以访问称为 ``调用context`` 的内容。 基本上你需要知道命令是如何执行的所有信息。 这包含很多有用的信息：

- :attr:`.Context.guild` 获取命令的 :class:`Guild`，如果有的话。
- :attr:`.Context.message` 获取命令的 :class:`Message`。
- :attr:`.Context.author` 获取调用命令的 :class:`Member` 或 :class:`User`。
- :meth:`.Context.send` 向使用该命令的通道发送消息。

context 实现了:class:`abc.Messageable` 接口，
所以你可以在 :class:`abc.Messageable` 上做的任何事情都可以在 :class:`~ext.commands.Context` 上做。

转换器
------------

添加带有函数参数的机器人参数只是定义机器人命令界面的第一步。 为了实际使用参数，我们通常希望将数据转换为目标类型。
我们称这些为 :ref:`ext_commands_api_converters`。

转换器有几种：

- 将参数作为唯一参数并返回不同类型的常规可调用对象。

    - 这些范围从你自己的函数到类似 :class:`bool` 或 :class:`int` 的东西。

- 从 :class:`~ext.commands.Converter` 继承的自定义类。

.. _ext_commands_basic_converters:

基本转换器
++++++++++++++++++

从本质上讲，基本转换器是一个可调用对象，它接收一个参数并将其转换为其他内容。

例如，如果我们想将两个数字相加，我们可以通过指定转换器来请求将它们转换为整数：

.. code-block:: python3

    @bot.command()
    async def add(ctx, a: int, b: int):
        await ctx.send(a + b)

我们使用称为 **函数注释** 的东西来指定转换器。 这是 Python 3 独有的特性，在 :pep:`3107` 中引入。

这适用于任何可调用对象，例如将字符串转换为全部大写的函数：

.. code-block:: python3

    def to_upper(argument):
        return argument.upper()

    @bot.command()
    async def up(ctx, *, content: to_upper):
        await ctx.send(content)

bool
^^^^^^

与其他基本转换器不同，:class:`bool` 转换器的处理方式略有不同。
不是直接转换为 :class:`bool` 类型，这将导致任何非空参数返回 ``True`` ，
而是根据参数将参数评估为 ``True`` 或 ``False`` 给定内容：

.. code-block:: python3

    if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on', '开', '打开', '启用', '是', '真'):
        return True
    elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off', '关', '关闭', '禁用', '否', '假'):
        return False

.. _ext_commands_adv_converters:

高级转换器
+++++++++++++++++++++

有时，基本转换器没有我们需要的足够信息。 例如，有时我们想从调用命令的 Message 中获取一些信息，或者我们想做一些异步处理。

为此，库提供了 :class:`~ext.commands.Converter` 接口。 这允许你访问 :class:`.Context` 并使可调用对象变成异步的。
使用这个接口定义一个自定义转换器需要覆盖一个方法，:meth:`.Converter.convert`。

一个示例转换器：

.. code-block:: python3

    import random

    class Slapper(commands.Converter):
        async def convert(self, ctx, argument):
            to_slap = random.choice(ctx.guild.members)
            return f'{ctx.author} 因为 {argument} 打了 {to_slap}'

    @bot.command()
    async def slap(ctx, *, reason: Slapper):
        await ctx.send(reason)

提供的转换器可以构建也可以不构建。 本质上这两个是等价的：

.. code-block:: python3

    @bot.command()
    async def slap(ctx, *, reason: Slapper):
        await ctx.send(reason)

    # 和

    @bot.command()
    async def slap(ctx, *, reason: Slapper()):
        await ctx.send(reason)

    # 是相同的...

构建转换器的可能性允许你在转换器的 ``__init__`` 中设置一些状态以微调转换器。
这方面的一个例子实际上在库中，:class:`~ext.commands.clean_content` 。

.. code-block:: python3

    @bot.command()
    async def clean(ctx, *, content: commands.clean_content):
        await ctx.send(content)

    # 或用于微调

    @bot.command()
    async def clean(ctx, *, content: commands.clean_content(use_nicknames=False)):
        await ctx.send(content)


如果转换器无法将参数转换为其指定的目标类型，则必须引发 :exc:`.BadArgument` 异常。

内联高级转换器
+++++++++++++++++++++++++++++

如果我们不想继承 :class:`~ext.commands.Converter`，我们仍然可以提供一个转换器，它具有高级转换器的高级功能，并且无需指定两种类型。
例如，一个常见的习惯用法是为该类创建一个类和一个转换器：

.. code-block:: python3

    class IDNName:
        def __init__(self, id, name):
            self.id = id
            self.name = name

        @property
        def result(self):
            return f"{self.id}{self.name}"

    class IDNNameConverter(commands.MemberConverter):
        async def convert(self, ctx, argument):
            member = await super().convert(ctx, argument)
            return IDNName(member.id, member.name)

    @bot.command()
    async def delta(ctx, *, member: JoinDistanceConverter):
        await ctx.send(member.result)

这可能会变得很烦，因此可以通过类型内部的 :func:`classmethod` 实现内联高级转换器：

.. code-block:: python3

    class IDNName:
        def __init__(self, id, name):
            self.id = id
            self.name = name

        @property
        def result(self):
            return f"{self.id}{self.name}"

        @classmethod
        async def convert(cls, ctx, argument):
            member = await commands.MemberConverter().convert(ctx, argument)
            return IDNName(member.id, member.name)

    @bot.command()
    async def delta(ctx, *, member: IDNName):
        await ctx.send(member.result)


QQ转换器
++++++++++++++++++++

在定义命令时，使用 :ref:`qq_api_models` 是一件相当常见的事情，因此该库使使用它们变得容易。

例如，要接收 :class:`Member` 你可以将其作为转换器传递：

.. code-block:: python3

    @bot.command()
    async def id(ctx, *, member: qq.Member):
        await ctx.send(f'{member} have a id of {member.id}')

执行此命令时，它会尝试将给定的字符串转换为一个 :class:`Member`，然后将其作为函数的参数传递。
这是通过检查字符串是提及、ID、昵称、用户名来工作的。
已将默认转换器集编写为尽可能易于使用。

很多qq模型都作为参数输出：

- :class:`Object`
- :class:`Member`
- :class:`User`
- :class:`Message`
- :class:`PartialMessage`
- :class:`abc.GuildChannel`
- :class:`TextChannel`
- :class:`VoiceChannel`
- :class:`CategoryChannel`
- :class:`AppChannel`
- :class:`LiveChannel`
- :class:`ThreadChannel`
- :class:`Guild`
- :class:`Role`
- :class:`Colour`

将其中任何一个设置为转换器将智能地将参数转换为你指定的适当目标类型。

在幕后，这些是由 :ref:`ext_commands_adv_converters` 接口实现的。 等效转换器表如下：

+--------------------------+-------------------------------------------------+
|          qq Class        |                    Converter                    |
+--------------------------+-------------------------------------------------+
| :class:`Object`          | :class:`~ext.commands.ObjectConverter`          |
+--------------------------+-------------------------------------------------+
| :class:`Member`          | :class:`~ext.commands.MemberConverter`          |
+--------------------------+-------------------------------------------------+
| :class:`User`            | :class:`~ext.commands.UserConverter`            |
+--------------------------+-------------------------------------------------+
| :class:`Message`         | :class:`~ext.commands.MessageConverter`         |
+--------------------------+-------------------------------------------------+
| :class:`PartialMessage`  | :class:`~ext.commands.PartialMessageConverter`  |
+--------------------------+-------------------------------------------------+
| :class:`.GuildChannel`   | :class:`~ext.commands.GuildChannelConverter`    |
+--------------------------+-------------------------------------------------+
| :class:`TextChannel`     | :class:`~ext.commands.TextChannelConverter`     |
+--------------------------+-------------------------------------------------+
| :class:`VoiceChannel`    | :class:`~ext.commands.VoiceChannelConverter`    |
+--------------------------+-------------------------------------------------+
| :class:`CategoryChannel` | :class:`~ext.commands.CategoryChannelConverter` |
+--------------------------+-------------------------------------------------+
| :class:`AppChannel`      | :class:`~ext.commands.AppChannelConverter`      |
+--------------------------+-------------------------------------------------+
| :class:`LiveChannel`     | :class:`~ext.commands.LiveChannelConverter`     |
+--------------------------+-------------------------------------------------+
| :class:`ThreadChannel`   | :class:`~ext.commands.ThreadChannelConverter`   |
+--------------------------+-------------------------------------------------+
| :class:`Guild`           | :class:`~ext.commands.GuildConverter`           |
+--------------------------+-------------------------------------------------+
| :class:`Role`            | :class:`~ext.commands.RoleConverter`            |
+--------------------------+-------------------------------------------------+
| :class:`Colour`          | :class:`~ext.commands.ColourConverter`          |
+--------------------------+-------------------------------------------------+

通过提供的转换器，我们可以将它们用作另一个转换器的构建块：

.. code-block:: python3

    class MemberID(commands.MemberConverter):
        async def convert(self, ctx, argument):
            member = await super().convert(ctx, argument)
            return member.id

    @bot.command()
    async def id(ctx, *, member: MemberID):
        """告诉你成员的 ID"""
        await ctx.send(f'我知道你的ID是 {member}')

.. _ext_commands_special_converters:

特殊转换器
++++++++++++++++++++

命令扩展还支持某些转换器，以允许超出通用线性解析的更高级和复杂的用例。
这些转换器允许你以易于使用的方式向你的命令引入一些更轻松和动态的语法。

typing.Union
^^^^^^^^^^^^^^

:data:`typing.Union` 是一个特殊的类型提示，它允许命令接受任何特定类型而不是单一类型。
例如，给定以下内容：

.. code-block:: python3

    import typing

    @bot.command()
    async def union(ctx, what: typing.Union[qq.TextChannel, qq.Member]):
        await ctx.send(what)


``what`` 参数将采用 :class:`qq.TextChannel` 转换器或 :class:`qq.Member` 转换器。
其工作方式是通过从左到右的顺序。
它首先尝试将输入转换为 :class:`qq.TextChannel`，如果失败，则尝试将其转换为 :class:`qq.Member`。
如果所有转换器都失败，则会引发一个特殊错误，:exc:`~ext.commands.BadUnionArgument`。

请注意，上面讨论的任何有效转换器都可以传递到 :data:`typing.Union` 的参数列表中。

typing.Optional
^^^^^^^^^^^^^^^^^

:data:`typing.Optional` 是一种特殊的类型提示，允许 “反向引用” 的行为。
如果转换器无法解析为指定的类型，解析器将跳过该参数，然后将 ``None`` 或指定的默认值传递给参数。然后解析器将继续处理下一个参数和转换器（如果有）。

考虑以下示例：

.. code-block:: python3

    import typing

    @bot.command()
    async def bottles(ctx, amount: typing.Optional[int] = 99, *, liquid="beer"):
        await ctx.send(f'墙上有 {amount} 瓶 {liquid}！')


.. image:: /images/commands/optional1.png

在这个例子中，由于参数不能被转换为一个 ``int``，默认的 ``99`` 被传递并且解析器继续处理，在这种情况下将把它传递到 ``liquid` ` 参数。

.. note::

    此转换器仅适用于常规位置参数，不适用于可变参数或仅关键字参数。

typing.Literal
^^^^^^^^^^^^^^^^

A :data:`typing.Literal` 是一种特殊的类型提示，它要求传递的参数在转换为相同类型后等于列出的值之一。
例如，给定以下内容：

.. code-block:: python3

    from typing import Literal

    @bot.command()
    async def shop(ctx, buy_sell: Literal['buy', 'sell'], amount: Literal[1, 2], *, item: str):
        await ctx.send(f'{buy_sell.capitalize()} {amount} {item}(s)!')


``buy_sell`` 参数必须是文字字符串 ``"buy"`` 或 ``"sell"`` 并且 ``amount`` 必须转换为 ``int`` ``1`` 或 ``2`` 。
如果 ``buy_sell`` 或 ``amount`` 不匹配任何值，则会引发一个特殊错误，:exc:`~.ext.commands.BadLiteralArgument`。
任何文字值都可以在同一个 :data:`typing.Literal` 转换器中混合和匹配。

注意 ``typing.Literal[True]`` 和 ``typing.Literal[False]`` 仍然遵循:class:`bool` 转换器规则。

Greedy
^^^^^^^^

:class:`~ext.commands.Greedy` 转换器是 :data:`typing.Optional` 转换器的泛化，但是应用于参数列表。
简单来说，这意味着它会尝试尽可能多地进行转换，直到无法进一步转换为止。

考虑以下示例：

.. code-block:: python3

    @bot.command()
    async def slap(ctx, members: commands.Greedy[qq.Member], *, reason='没有理由'):
        slapped = ", ".join(x.name for x in members)
        await ctx.send(f'{slapped} 只是因为 {reason} 被扇了耳光')

调用时，它允许传入任意数量的成员：

.. image:: /images/commands/greedy1.png

使用此转换器时传递的类型取决于它所附加的参数类型：

- 位置参数类型将接收默认参数或转换值的列表。
- 变量参数类型将像往常一样是 :class:`tuple` 。
- 仅关键字参数类型将与 :class:`~ext.commands.Greedy` 完全没有传递一样。

:class:`~ext.commands.Greedy` 参数也可以通过指定一个可选值来成为可选的。

当与 :data:`typing.Optional` 转换器混合使用时，你可以提供简单而富有表现力的命令调用语法：

.. code-block:: python3

    import typing

    @bot.command()
    async def kick(ctx, members: commands.Greedy[qq.Member],
                       reason: typing.Optional[str]):
        """使用可选的 delete_days 参数大规模剔除成员"""
        for member in members:
            await member.kick(reason=reason)


可以通过以下任何一种方式调用此命令：

.. code-block:: none

    $kick @Member @Member2 刷屏 机器人
    $kick @Member @Member2
    $kick @Member 刷屏

.. warning::

    :class:`~ext.commands.Greedy` 和 :data:`typing.Optional` 的使用功能强大且有用，
    但要付出代价，它们会使你面临一些解析上的歧义，这可能会让某些人感到惊讶。

    例如，期望 :data:`typing.Optional` 的 :class:`qq.Member` 后跟 :class:`int` 的会捕获到本来期望传到 :class:`int` 的参数，
    却因为 :class:`~ext.commands.MemberConverter` 支持使用 ID 而获取到了 :class:`qq.Member`。
    你应该注意不要在代码中引入意外的解析歧义。一种技术是通过自定义转换器限制允许的预期语法或重新排序参数以最大程度地减少冲突。

    为了帮助解决一些解析歧义，:class:`str`、`None`、:data:`typing.Optional` 和 :class:`~ext.commands.Greedy`
    被禁止作为 :class:`~ext.commands.Greedy` 转换器的参数。

.. _ext_commands_error_handler:

Error Handling
----------------

当我们的命令无法解析时，默认情况下，我们会在控制台的 ``stderr`` 中收到一个嘈杂的错误，告诉我们发生了错误并且已被默默忽略。

为了处理我们的错误，我们必须使用称为错误处理程序的东西。有一个全局错误处理程序，称为 :func:`.on_command_error`，
它的工作方式与 :ref:`qq-api-events` 中的任何其他事件一样。每个到达的错误都会调用这个全局错误处理程序。

然而，大多数时候，我们想要处理命令本身的本地错误。幸运的是，命令带有本地错误处理程序，允许我们这样做。
首先我们用 :meth:`.Command.error` 装饰一个错误处理函数：

.. code-block:: python3

    @bot.command()
    async def info(ctx, *, member: qq.Member):
        """告诉你一些关于成员的信息。"""
        msg = f'{member} 的 ID 为 {member.joined_at} 并且有 {len(member.roles)} 个身份组。'
        await ctx.send(msg)

    @info.error
    async def info_error(ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send('我找不到那个成员...')

错误处理程序的第一个参数是 :class:`.Context`，而第二个参数是派生自:exc:`~ext.commands.CommandError` 的异常。
在文档的 :ref:`ext_commands_api_errors` 页面中可以找到错误列表。

检查
-------

在某些情况下，我们不希望用户使用我们的命令。
他们没有这样做的权限，或者我们之前阻止了他们使用我们的机器人。
命令扩展在一个称为 :ref:`ext_commands_api_checks` 的概念中完全支持这些东西。

检查是一个基本谓词，可以将 :class:`.Context` 作为其唯一参数。在其中，你有以下选项：

- 返回 ``True`` 表示此人可以运行该命令。
- 返回 ``False`` 表示此人无法运行该命令。
- 引发一个 :exc:`~ext.commands.CommandError` 派生异常以表示此人无法运行该命令。

    - 这允许你在 :ref:`错误处理程序 <ext_commands_error_handler>` 中处理自定义错误消息。

要注册一个命令的检查，我们有两种方法可以这样做。第一种是使用 :meth:`~ext.commands.check` 装饰器。例如：

.. code-block:: python3

    async def is_owner(ctx):
        return ctx.author.id == 114514

    @bot.command(name='eval')
    @commands.check(is_owner)
    async def _eval(ctx, *, code):
        """eval 命令的一个坏例子"""
        await ctx.send(eval(code))

如果函数 ``is_owner`` 返回 ``True`` ，这会运行命令。

有时我们经常重复使用一个检查，并希望将它拆分成它自己的装饰器。为此，我们可以添加另一个深度级别：

.. code-block:: python3

    def is_owner():
        async def predicate(ctx):
            return ctx.author.id == 114514
        return commands.check(predicate)

    @bot.command(name='eval')
    @is_owner()
    async def _eval(ctx, *, code):
        """eval 命令的一个坏例子"""
        await ctx.send(eval(code))


由于所有者检查如此普遍，库为你提供了它（:func:`~ext.commands.is_owner`）：

.. code-block:: python3

    @bot.command(name='eval')
    @commands.is_owner()
    async def _eval(ctx, *, code):
        """eval 命令的一个坏例子"""
        await ctx.send(eval(code))

当指定多个检查时， **所有** 检查都必须为“True”：

.. code-block:: python3

    def is_in_guild(guild_id):
        async def predicate(ctx):
            return ctx.guild and ctx.guild.id == guild_id
        return commands.check(predicate)

    @bot.command()
    @commands.is_owner()
    @is_in_guild(114514)
    async def secretguilddata(ctx):
        """超级秘密的东西"""
        await ctx.send('秘密的东西')

如果以上示例中的任何检查失败，则不会运行该命令。

当错误发生时，错误会传播到 :ref:`错误处理程序 <ext_commands_error_handler>`。
如果你不引发自定义 :exc:`~ext.commands.CommandError` 派生异常，那么它将被包装为 :exc:`~ext.commands.CheckFailure` 异常，如下所示：

.. code-block:: python3

    @bot.command()
    @commands.is_owner()
    @is_in_guild(114514)
    async def secretguilddata(ctx):
        """超级秘密的东西"""
        await ctx.send('秘密的东西')

    @secretguilddata.error
    async def secretguilddata_error(ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send('没什么可看的同志。')

如果你想要一个更健壮的错误系统，你可以从异常派生并引发它而不是返回 ``False`` ：

.. code-block:: python3

    class NoPrivateMessages(commands.CheckFailure):
        pass

    def guild_only():
        async def predicate(ctx):
            if ctx.guild is None:
                raise NoPrivateMessages('别给我发私聊!')
            return True
        return commands.check(predicate)

    @guild_only()
    async def test(ctx):
        await ctx.send('很好！这不是一个私聊！')

    @test.error
    async def test_error(ctx, error):
        if isinstance(error, NoPrivateMessages):
            await ctx.send(error)

.. note::

    由于 ``guild_only`` 装饰器很常见，它通过 :func:`~ext.commands.guild_only` 内置。

全局检查
++++++++++++++

有时我们想对每个命令进行检查，而不仅仅是某些命令。该库也使用全局检查概念支持这一点。

全局检查的工作方式与常规检查类似，只是它们是使用 :meth:`.Bot.check` 装饰器注册的。

例如，要阻止所有私聊，我们可以执行以下操作：

.. code-block:: python3

    @bot.check
    async def globally_block_dms(ctx):
        return ctx.guild is not None

.. warning::

    在编写全局检查时要小心，因为它也可能将你锁定在自己的机器人之外。
