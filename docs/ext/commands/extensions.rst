.. currentmodule:: discord

.. _ext_commands_extensions:

扩展
=============

在机器人开发中会出现一段时间，当你想要在运行时扩展机器人功能并快速卸载和重新加载代码（也称为热加载）。
命令框架内置了这种能力，有一个称为扩展的概念。

介绍
--------

扩展的核心是一个 python 文件，它有一个名为 ``setup`` 的入口点。
这个设置必须是一个普通的 Python 函数（不是协程）。它需要一个参数，加载扩展的 :class:`~.commands.Bot`。

示例扩展如下所示：

.. code-block:: python3
    :caption: hello.py
    :emphasize-lines: 7,8

    from qq.ext import commands

    @commands.command()
    async def hello(ctx):
        await ctx.send(f'你好 {ctx.author.display_name}。')

    def setup(bot):
        bot.add_command(hello)

在这个例子中，我们定义了一个简单的命令，当扩展加载时，这个命令被添加到机器人中。
现在最后一步是加载扩展，我们通过调用 :meth:`.Bot.load_extension` 来完成。为了加载这个扩展，我们调用 ``bot.load_extension('hello')`` 。

.. admonition:: Cogs
    :class: helpful

    扩展通常与齿轮结合使用。要了解更多关于它们的信息，请查看文档，:ref:`ext_commands_cogs`。

.. note::

扩展路径似于导入机制。这意味着如果有一个文件夹，那么它必须是点限定的。
例如，要在 ``plugins/hello.py`` 中加载扩展，我们需要使用字符串 ``plugins.hello``。

重装
-----------

当你对扩展进行更改并想要重新加载引用时，该库附带了一个函数来为你执行此操作，:meth:`.Bot.reload_extension`。

.. code-block:: python3

    >>> bot.reload_extension('hello')

一旦扩展重新加载，我们所做的任何更改都将被应用。如果我们想在不重新启动机器人的情况下添加或删除功能，这将非常有用。如果在重新加载过程中发生错误，机器人将假装从未发生过重新加载。

卸载
-------------

虽然很少见，但有时扩展需要清理或知道何时卸载。对于这样的情况，还有另一个名为 ``teardown`` 的入口点，它类似于 ``setup`` ，但是在卸载扩展时调用。

.. code-block:: python3
    :caption: basic_ext.py

    def setup(bot):
        print('我正在加载！')

    def teardown(bot):
        print('我正在被卸载！')
