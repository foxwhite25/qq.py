.. currentmodule:: qq

.. _ext_commands_cogs:

齿轮
======

在你开发机器人的过程中，你可能会想要将命令、监听器、或者某些状态包装到一个类里面，齿轮 （Cog）就可以让你做到这一点。

大概原理：

- 每个齿轮都是一个 Python 类，它是 :class:`.commands.Cog` 的子类。
- 每个命令都标有:func:`.commands.command` 装饰器。
- 每个侦听器都标有 :meth:`.commands.Cog.listener` 装饰器。
- 然后使用 :meth:`.Bot.add_cog` 调用注册齿轮。
- 随后通过 :meth:`.Bot.remove_cog` 调用移除齿轮。

应该注意的是，齿轮通常与 :ref:`ext_commands_extensions` 一起使用。

快速示例
---------------

这个示例 cog 为你的命令定义了一个 ``Greetings`` 类别，带有一个名为 ``hello`` 的 :ref:`命令 <ext_commands_commands>`
以及一个监听 :ref:`事件 <qq-api-events>`。

.. code-block:: python3

    class Greetings(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self._last_member = None

        @commands.Cog.listener()
        async def on_ready(self):
            print(f'以 {self.bot.user} 身份登录（ID：{self.bot.user.id}）')
            print('------')

        @commands.command()
        async def hello(self, ctx, *, member: qq.Member = None):
            """说你好"""
            member = member or ctx.author
            if self._last_member is None or self._last_member.id != member.id:
                await ctx.send(f'你好{member.name}~')
            else:
                await ctx.send(f'你好{member.name}... 这感觉很熟悉。')
            self._last_member = member

需要考虑的几个技术说明：

- 所有监听器都必须通过装饰器显式标记，:meth:`~.commands.Cog.listener`。
- 齿轮的名称自动从类名派生，但可以覆盖。 参见 :ref:`ext_commands_cogs_meta_options` 。
- 所有命令都必须采用 ``self`` 参数以允许使用可用于 ``state`` 属性。

齿轮注册
-------------------

一旦你定义了你的齿轮，你需要告诉机器人注册要使用的齿轮。 我们通过 :meth:`~.commands.Bot.add_cog` 方法来做到这一点。

.. code-block:: python3

    bot.add_cog(Greetings(bot))

这会将齿轮绑定到机器人，自动将所有命令和监听器添加到机器人。

请注意，我们可以通过名称引用齿轮，名称可以通过 :ref:`ext_commands_cogs_meta_options` 覆盖。
如果我们最终想要移除齿轮，我们将执行以下操作。

.. code-block:: python3

    bot.remove_cog('Greetings')

使用齿轮
-------------

就像我们通过名字移除一个齿轮一样，我们也可以通过它的名字来检索它。
这允许我们使用齿轮作为命令间通信协议来共享数据。 例如：

.. code-block:: python3
    :emphasize-lines: 22,24

    class Economy(commands.Cog):
        ...

        async def withdraw_money(self, member, money):
            # 在这里实现
            ...

        async def deposit_money(self, member, money):
            # 在这里实现
            ...

    class Gambling(commands.Cog):
        def __init__(self, bot):
            self.bot = bot

        def coinflip(self):
            return random.randint(0, 1)

        @commands.command()
        async def gamble(self, ctx, money: int):
            """赌点钱。"""
            economy = self.bot.get_cog('Economy')
            if economy is not None:
                await economy.withdraw_money(ctx.author, money)
                if self.coinflip() == 1:
                    await economy.deposit_money(ctx.author, money * 1.5)

.. _ext_commands_cogs_special_methods:

特殊方法
-----------------

随着齿轮变得越来越复杂并拥有更多命令，我们需要自定义整个齿轮或机器人的行为。

它们如下：

- :meth:`.Cog.cog_unload`
- :meth:`.Cog.cog_check`
- :meth:`.Cog.cog_command_error`
- :meth:`.Cog.cog_before_invoke`
- :meth:`.Cog.cog_after_invoke`
- :meth:`.Cog.bot_check`
- :meth:`.Cog.bot_check_once`

你可以访问参考资料以获取更多详细信息。

.. _ext_commands_cogs_meta_options:

元选项
--------------

齿轮的核心是一个元类，:class:`.commands.CogMeta`，它可以采用各种选项来定制一些行为。
要做到这样，我们将关键字参数传递给类定义行。 例如，要更改齿轮名称，我们可以传递 ``name`` 关键字参数，如下所示：

.. code-block:: python3

    class MyCog(commands.Cog, name='我的第一个齿轮'):
        pass

要查看你可以设置的更多选项，请参阅 :class:`.commands.CogMeta` 的文档。

检查
------------

由于齿轮是类，因此我们有一些工具可以帮助我们检查齿轮的某些属性。

要获取命令的 :class:`list`，我们可以使用 :meth:`.Cog.get_commands`。 ::

    >>> cog = bot.get_cog('Greetings')
    >>> commands = cog.get_commands()
    >>> print([c.name for c in commands])

如果我们也想获得子命令，我们可以使用 :meth:`.Cog.walk_commands` 生成器。 ::

    >>> print([c.qualified_name for c in cog.walk_commands()])

要对监听器执行相同操作，我们可以使用 :meth:`.Cog.get_listeners` 查询它们。
这将返回一个元组列表，第一个元素是监听器名称，第二个元素是实际的函数本身。 ::

    >>> for name, func in cog.get_listeners():
    ...     print(name, '->', func)

