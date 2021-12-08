:orphan:

.. currentmodule:: discord
.. _faq:

经常问的问题
===========================

这是有关使用 ``qq.py`` 及其扩展模块的常见问题列表。随意提出一个新问题或通过Pull Request提交一个。

.. contents:: Questions
    :local:

Coroutines
------------

关于协程和 asyncio 的问题属于这里。

什么是协程？
~~~~~~~~~~~~~~~~~~~~~~

|coroutine_link|_ 是一个必须使用 ``await`` 或 ``yield from`` 调用的函数。
当 Python 遇到 ``await`` 时，它会在那个点停止函数的执行并处理其他事情，直到它回到那个点并完成它的工作。
这允许你的程序同时执行多项操作，而无需使用线程或复杂的多处理。

**如果你忘记 await 协程，则协程将不会运行。永远不要忘记 await 协程。**

我在哪里可以使用 ``await``\？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

你只能在 ``async def`` 函数中使用 ``await``，而不能在其他任何地方使用。

“阻塞”是什么意思？
~~~~~~~~~~~~~~~~~~~~~~~~~~~

在异步编程中，阻塞调用本质上是函数中所有不是 ``await`` 的部分。但是不要绝望，因为并非所有形式的阻塞都是不好的！
使用阻塞调用是不可避免的，但你必须努力确保不会过度阻塞函数。
请记住，如果你阻塞的时间过长，那么你的机器人将冻结，因为它此时尚未停止函数的执行以执行其他操作。

如果启用日志记录，此库将尝试警告你正在发生阻塞并显示消息：
``心跳被阻塞超过 N 秒。``
有关启用日志记录的详细信息，请参阅 :ref:`logging_setup`。

阻塞时间过长的常见原因是 :func:`time.sleep`。不要那样做。使用 :func:`asyncio.sleep` 代替。类似于这个例子： ::

    # 坏坏
    time.sleep(10)

    # 很好
    await asyncio.sleep(10)

阻塞时间过长的另一个常见原因是使用带有著名模块 :doc:`req:index` 的 HTTP 请求。
虽然 :doc:`req:index` 是非异步编程的一个了不起的模块，但它不是 :mod:`asyncio` 的好选择，因为某些请求可能会阻塞事件循环太久。
相反，请使用 :doc:`aiohttp <aio:index>` 库。

考虑以下示例： ::

    # 坏坏
    r = requests.get('http://aws.random.cat/meow')
    if r.status_code == 200:
        js = r.json()
        await channel.send(js['file'])

    # 很好
    async with aiohttp.ClientSession() as session:
        async with session.get('http://aws.random.cat/meow') as r:
            if r.status == 200:
                js = await r.json()
                await channel.send(js['file'])

通用
---------

关于库使用的一般问题属于这里。

在哪里可以找到使用示例？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

示例代码可以在 `示例文件夹 <https://github.com/foxwhite25/qq.py/tree/master/examples>`_ 找到。

如何向特定频道发送消息？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

你必须直接获取通道，然后调用适当的方法。 例子： ::

    channel = client.get_channel(12324234183172)
    await channel.send('hello')

我如何私聊？
~~~~~~~~~~~~~~~~~~~

目前官方还没有支持私聊

如何获取已发送消息的 ID？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:meth:`abc.Messageable.send` 返回发送的:class:`Message`。
消息的 ID 可以通过 :attr:`Message.id` 访问： ::

     message = await channel.send('嗯...')
     message_id = message.id

如何上传图片？
~~~~~~~~~~~~~~~~~~~~~~~~~

要将某些内容上传到 QQ，你必须使用 :class:`File` 对象。

A :class:`File` 接受两个参数，类文件对象（或文件路径）和上传时传递给 QQ 的文件名。

如果你想上传一张图片，它很简单： ::

    await channel.send(file=qq.File('my_file.png'))

如果你有一个类似文件的对象，你可以执行以下操作： ::

    with open('my_file.png', 'rb') as fp:
        await channel.send(file=discord.File(fp, 'new_filename.png'))

要上传多个文件，你可以使用 ``files`` 关键字参数代替 ``file``\： ::

    my_files = [
        qq.File('result.zip'),
        qq.File('teaser_graph.png'),
    ]
    await channel.send(files=my_files)

如果你想从一个 URL 上传一些东西，你必须使用 :doc:`aiohttp <aio:index>` 来使用 HTTP 请求
然后像这样传递一个 :class:`io.BytesIO` 实例给 :class:`File`：

.. code-block:: python3

    import io
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.get(my_url) as resp:
            if resp.status != 200:
                return await channel.send('无法下载文件...')
            data = io.BytesIO(await resp.read())
            await channel.send(file=qq.File(data, 'cool_image.png'))


如何向消息添加表情？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

目前官方还没有支持

我如何在后台运行一些东西？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`检查 background_task.py 示例。 <https://github.com/foxwhite25/qq.py/blob/master/examples/background_task.py>`_

我如何获得特定对象？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

有多种方法可以做到这一点。 如果你有特定对象的 ID，则可以使用以下功能之一：

- :meth:`Client.get_channel`
- :meth:`Client.get_guild`
- :meth:`Client.get_user`
- :meth:`Guild.get_member`
- :meth:`Guild.get_channel`
- :meth:`Guild.get_role`

以下使用 HTTP 请求：

- :meth:`Client.fetch_user`
- :meth:`Client.fetch_guilds`
- :meth:`Client.fetch_guild`
- :meth:`Guild.fetch_member`


如果上述函数对你没有帮助，那么使用 :func:`utils.find` 或 :func:`utils.get` 将有助于查找特定对象。

快速示例： ::

    # 按名称查找频道
    guild = qq.utils.get(client.guilds, name='My Server')

    # 确保检查它是否被找到
    if guild is not None:
        # 按名称查找子频道
        channel = discord.utils.get(guild.text_channels, name='cool-channel')

如何发出网络请求？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

要发出请求，你应该使用非阻塞库。
这个库已经使用并需要一个 第三方库来发出请求，:doc:`aiohttp <aio:index>`。

快速示例: ::

    async with aiohttp.ClientSession() as session:
        async with session.get('http://aws.random.cat/meow') as r:
            if r.status == 200:
                js = await r.json()

有关更多信息，请参阅 `aiohttp 的完整文档 <http://aiohttp.readthedocs.io/en/stable/>`_ 。

命令扩展
-------------------

 ``discord.ext.commands`` 有关的问题。

为什么定义 ``on_message`` 之后我的命令用不了了？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

覆盖默认提供的 ``on_message`` 禁止运行任何额外的命令。 要解决此问题，请在 “on_message” 末尾添加 “bot.process_commands(message)” 行。 例如： ::

    @bot.event
    async def on_message(message):
        # 在这里做一些额外的事情

        await bot.process_commands(message)

或者，你可以将 ``on_message`` 逻辑放入 **listener**。 在此设置中，你不应该手动调用 “bot.process_commands()” 。 这也允许你异步地做多项响应到一条消息。 例子::

    @bot.listen('on_message')
    async def whatever_you_want_to_call_it(message):
        # 在这里做事
        # 这里不处理命令

为什么我的参数需要引号?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

在一个简单的命令中定义为： ::

    @bot.command()
    async def echo(ctx, message: str):
        await ctx.send(message)

通过 ``?echo a b c`` 调用它只会获取第一个参数而忽略其余参数。 要解决此问题，你需要在边上加上引号 ``?echo "a b c"`` 或添加多个你需要的参数。 例子： ::

    @bot.command()
    async def echo(ctx, a, b, c, message: str):
        await ctx.send(message)

这将允许你使用 ``?echo a b c`` 而不需要引号。

我如何获得原始的 “Message” \？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~ext.commands.Context` 包含该属性，使用:attr:`~.Context.message` 获取原始信息。

例子: ::

    @bot.command()
    async def length(ctx):
        await ctx.send(f'你的留言是 {len(ctx.message.content)} 字符长度。')

如何创建子命令？
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

使用 :func:`~ext.commands.group` 装饰器。 这会将回调转换为 :class:`~ext.commands.Group` ，它允许你将命令添加到作为“子命令”运行的组。 这些组也可以任意嵌套。

例子: ::

    @bot.group()
    async def git(ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('传递了无效的 git 命令...')

    @git.command()
    async def push(ctx, remote: str, branch: str):
        await ctx.send(f'Pushing to {remote} {branch}')

这可以用作 ``?git push origin master``。
