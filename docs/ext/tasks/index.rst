.. _discord_ext_tasks:

``discord.ext.tasks`` -- asyncio.Task 助手
====================================================

.. versionadded:: 1.1.0

制作机器人时最常见的操作之一是以指定的时间间隔在后台运行循环。 这种模式很常见，但有很多你需要注意的事情：

- 我如何处理 :exc:`asyncio.CancelledError`？
- 如果互联网不可用，我该怎么办？
- 无论如何，我可以断线的最大秒数是多少？

这个 qq.py 扩展的目标是让你摆脱所有这些担忧。

教程
---------

一个简单的后台任务:class:`~discord.ext.commands.Cog`:

.. code-block:: python3

    from qq.ext import tasks, commands

    class MyCog(commands.Cog):
        def __init__(self):
            self.index = 0
            self.printer.start()

        def cog_unload(self):
            self.printer.cancel()

        @tasks.loop(seconds=5.0)
        async def printer(self):
            print(self.index)
            self.index += 1

在重新连接期间添加要处理的异常：

.. code-block:: python3

    import asyncpg
    from qq.ext import tasks, commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot = bot
            self.data = []
            self.batch_update.add_exception_type(asyncpg.PostgresConnectionError)
            self.batch_update.start()

        def cog_unload(self):
            self.batch_update.cancel()

        @tasks.loop(minutes=5.0)
        async def batch_update(self):
            async with self.bot.pool.acquire() as con:
                # batch update here...
                pass

退出前循环一定次数：

.. code-block:: python3

    from discord.ext import tasks

    @tasks.loop(seconds=5.0, count=5)
    async def slow_count():
        print(slow_count.current_loop)

    @slow_count.after_loop
    async def after_slow_count():
        print('done!')

    slow_count.start()

在循环开始之前等待机器人准备就绪：

.. code-block:: python3

    from discord.ext import tasks, commands

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.index = 0
            self.bot = bot
            self.printer.start()

        def cog_unload(self):
            self.printer.cancel()

        @tasks.loop(seconds=5.0)
        async def printer(self):
            print(self.index)
            self.index += 1

        @printer.before_loop
        async def before_printer(self):
            print('waiting...')
            await self.bot.wait_until_ready()

在取消期间做某事：

.. code-block:: python3

    from discord.ext import tasks, commands
    import asyncio

    class MyCog(commands.Cog):
        def __init__(self, bot):
            self.bot= bot
            self._batch = []
            self.lock = asyncio.Lock()
            self.bulker.start()

        async def do_bulk(self):
            # bulk insert data here
            ...

        @tasks.loop(seconds=10.0)
        async def bulker(self):
            async with self.lock:
                await self.do_bulk()

        @bulker.after_loop
        async def on_bulker_cancel(self):
            if self.bulker.is_being_cancelled() and len(self._batch) != 0:
                # if we're cancelled and we have some data left...
                # let's insert it to our database
                await self.do_bulk()


.. _ext_tasks_api:

API 参考
---------------

.. attributetable:: discord.ext.tasks.Loop

.. autoclass:: discord.ext.tasks.Loop()
    :members:
    :special-members: __call__
    :exclude-members: after_loop, before_loop, error

    .. automethod:: Loop.after_loop()
        :decorator:

    .. automethod:: Loop.before_loop()
        :decorator:

    .. automethod:: Loop.error()
        :decorator:

.. autofunction:: discord.ext.tasks.loop
