:orphan:

.. _quickstart:

.. currentmodule:: qq

快速开始
============

本页简要介绍了该库。它假定你已安装该库，如果你还没有安装，请前往 :ref:`installing` 的部分。

一个最小的机器人
---------------

让我们制作一个响应特定消息的机器人并引导你完成它。它看起来像这样：

.. code-block:: python3

    import qq

    client = qq.Client()

    @client.event
    async def on_ready():
        print(f'我们使用 {client.user} 成功登陆了')

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        if message.content.startswith('$你好'):
            await message.channel.send('你好!')

    client.run('your token here')

让我们命名这个文件 ``example_bot.py``.确保不要命名它为``qq.py`` ，因为那会和库冲突。

这里发生了很多事情，让我们一步一步地引导你完成。

1.  第一行只是导入库。
    如果这引发了 `ModuleNotFoundError` 或 `ImportError` ，请转到 :ref:`installing` 部分来安装。

2.  接下来，我们创建一个实例 :class:`Client`。
    这个客户端是我们与 QQ 的连接。

3.  然后我们使用 :meth:`Client.event` 装饰器来注册一个事件。这库有很多事件可以给你选择。
    由于这个库是异步的，我们以“回调”风格的方式做事。

    回调本质上是一个在发生某些事情时调用的函数。 在我们的案例中，当机器人完成登录时触发 :func:`on_ready`
    并且当机器人收到消息时调用事件时候触发 :func:`on_message` 。
4.  由于 :func:`on_message` 接收到的 **每条消息** 都会触发事件， 我们必须确保我们忽略来自自己的信息。
    我们通过检查 :attr:`Message.author` 是否和 :attr:`Client.user` 是一样的。
5.  之后，我们检查 :class:`Message.content` 是否以 ``'$你好'`` 开始。
    如果是，那么我们在它使用的通道中发送一条消息 ``'你好!'``。
    这是处理命令的基本方法，以后可以使用 :doc:`./ext/commands/index` 框架。
6.  最后，我们使用登录令牌运行机器人。
    如果你在获取令牌或创建机器人方面需要帮助，请查看 :ref:`qq-intro` 的部分。


现在我们已经制作了一个机器人，我们必须 **运行** 机器人。
幸运的是，这很简单，因为这只是一个 Python 脚本，我们可以直接运行它。

在 Windows 上：

.. code-block:: shell

    $ py -3 example_bot.py

在其他系统上：

.. code-block:: shell

    $ python3 example_bot.py

现在你可以尝试使用你的基本机器人。