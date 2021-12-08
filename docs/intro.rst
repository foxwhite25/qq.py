:orphan:

.. currentmodule:: qq

.. _intro:

引言
==============

这是 qq.py 的文档，这是一个用于帮助创建利用 QQ Channel API 的应用程序的 Python 库。

先决条件
---------------

qq.py 适用于 Python 3.8 或更高版本。不提供对早期 Python 版本的支持。
不支持 Python 2.7 或更低版本。不支持 Python 3.7 或更低版本。

.. _installing:

安装
-----------

你可以直接从 PyPI 获取库: ::

    python3 -m pip install -U discord.py

如果你使用的是 Windows，则应使用以下内容代替: ::

    py -3 -m pip install -U discord.py

虚拟环境
~~~~~~~~~~~~~~~~~~~~~

有时你希望防止库污染系统安装或使用与系统上安装的库不同的库版本。你可能也无权在系统范围内安装库。
为此，Python 3.3 的标准库附带了一个称为“虚拟环境”的概念，以帮助维护这些单独的版本。

更深入的教程可在 :doc:`py:tutorial/venv` 找到。

然而，以下是一个快速创建的方法：

1. 转到你项目的工作目录:

    .. code-block:: shell

        $ cd your-bot-source
        $ python3 -m venv bot-env

2. 激活虚拟环境:

    .. code-block:: shell

        $ source bot-env/bin/activate

    在 Windows 上激活:

    .. code-block:: shell

        $ bot-env\Scripts\activate.bat

3. 像往常一样使用 pip:

    .. code-block:: shell

        $ pip install -U qq.py

恭喜。你现在已经设置了一个虚拟环境。

基本概念
---------------

qq.py 围绕着 :ref:`事件 <discord-api-events>` 运作。
事件是你收听然后响应的内容。例如，当一条消息发生时，你将收到一个可以响应的事件。

展示事件如何工作的一个快速示例：

.. code-block:: python3

    import discord

    class MyClient(discord.Client):
        async def on_ready(self):
            print(f'Logged on as {self.user}!')

        async def on_message(self, message):
            print(f'Message from {messsage.author}: {message.content}')

    client = MyClient()
    client.run('my token goes here')
