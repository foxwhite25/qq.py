.. currentmodule:: qq

API 参考
===============

以下部分概述了 qq.py 的 API。

.. note::

    此模块使用 Python 日志记录模块以独立于输出的方式记录诊断和错误。
    如果没有配置日志模块，这些日志将不会输出到任何地方。
    有关如何使用 qq.py 设置和使用日志记录模块的更多信息，请参阅 :ref:`logging_setup`。

版本相关信息
---------------------

查询库的版本信息主要有两种方式。

.. data:: version_info

    一个命名元组，类似于 :obj:`py:sys.version_info`.

    就像 :obj:`py:sys.version_info` ， ``releaselevel`` 的有效值为
     ``alpha`` 、 ``beta`` 、 ``candidate`` 和 ``final`` 。

.. data:: __version__

    版本的字符串表示。 e.g. ``'1.0.0rc1'``。 这是基于 :pep:`440` 。

客户端
--------

Client
~~~~~~~

.. attributetable:: Client

.. autoclass:: Client
    :members:
    :exclude-members: fetch_guilds, event

    .. automethod:: Client.event()
        :decorator:

    .. automethod:: Client.fetch_guilds
        :async-for:

AutoShardedClient
~~~~~~~~~~~~~~~~~~

.. attributetable:: AutoShardedClient

.. autoclass:: AutoShardedClient
    :members:


事件参考
---------------

本节概述了 :class:`Client` 监听的不同类型的事件。

注册事件有两种方式，第一种方式是通过使用:meth:`Client.event`。第二种方法是通过子类化 :class:`Client` 并覆盖特定事件。例如： ::

    import qq

    class MyClient(qq.Client):
        async def on_message(self, message):
            if message.author == self.user:
                return

            if message.content.startswith('$hello'):
                await message.channel.send('Hello World!')


如果事件处理程序引发异常， :func:`on_error` 将被调用来处理它，默认打印回溯并忽略异常。

.. warning::

    所有事件都必须是 |coroutine_link|_。如果不是，那么你可能会遇到意外错误。为了将函数转换为协程，它们必须是“async def”函数。

.. function:: on_connect()

    当客户端成功连接到 QQ 时调用。这与客户端完全准备好不同，请参阅:func:`on_ready`。 :func:`on_ready` 上的警告也适用。

.. function:: on_shard_connect(shard_id)

    类似于:func:`on_connect`，除了被:class:`AutoShardedClient` 用来表示特定分片 ID 何时连接到 QQ。

    .. versionadded:: 1.4

    :param shard_id: 已连接的分片 ID。
    :type shard_id: :class:`int`

.. function:: on_disconnect()

    当客户端与 QQ 断开连接或尝试连接 QQ 失败时调用。
    这可能通过互联网断开、明确调用关闭或 QQ 以一种或另一种方式终止连接而发生。

    这个函数可以在没有相应的:func:`on_connect` 调用的情况下被多次调用。

.. function:: on_shard_disconnect(shard_id)

    类似于:func:`on_disconnect`，除了被:class:`AutoShardedClient` 用来表示特定分片 ID 何时与 QQ 断开连接。

    .. versionadded:: 1.4

    :param shard_id: 已断开连接的分片 ID。
    :type shard_id: :class:`int`

.. function:: on_ready()

    当客户端准备好从 QQ 接收到的数据时调用。通常在登录成功后 :attr:`Client.guilds` 和 co. 被填满后。

    .. warning::

    此函数不能保证是第一个调用的事件。同样，这个函数也 **不能** 保证只被调用一次。
    库实现了重新连接逻辑，因此只要 RESUME 请求失败，就会最终调用此事件。

.. function:: on_shard_ready(shard_id)

    类似于:func:`on_ready`，除了被:class:`AutoShardedClient` 用来表示特定分片ID 何时准备就绪。

    :param shard_id: 准备好的分片 ID。
    :type shard_id: :class:`int`

.. function:: on_resumed()

    当客户端恢复会话时调用。

.. function:: on_shard_resumed(shard_id)

    类似于:func:`on_resumed`，除了被:class:`AutoShardedClient` 用来表示特定分片ID 何时恢复会话。

    .. versionadded:: 1.4

    :param shard_id: 已恢复的分片 ID。
    :type shard_id: :class:`int`

.. function:: on_error(event, *args, **kwargs)

    通常，当事件引发未捕获的异常时，会将回溯打印到 stderr 并忽略异常。
    如果你想更改此行为并出于任何原因自己处理异常，则可以覆盖此事件。完成后，将取消打印回溯的默认操作。

    引发异常的信息和异常本身可以通过标准调用 :func:`sys.exc_info` 来检索。

    如果你希望异常从 :class:`Client` 类传播出去，你可以定义一个 ``on_error`` 处理程序，它由一个空的 :ref:`raise 语句 <py:raise>` 组成。
    ``on_error`` 引发的异常不会以任何方式由 :class:`Client` 处理。

    .. note::

        ``on_error`` 只会被分派到 :meth:`Client.event`。

        它不会被 :meth:`Client.wait_for` 接收，或者，如果有使用，:ref:`ext_commands_api_bot` 侦听器，
        例如 :meth:`~ext.commands.Bot.listen` 或 :meth:`~ext.commands.Cog.listener`。

    :param event: 引发异常的事件的名称。
    :type event: :class:`str`

    :param args: 引发异常的事件的位置参数。
    :param kwargs: 引发异常的事件的关键字参数。

.. function:: on_socket_event_type(event_type)

    每当从 WebSocket 接收到 websocket 事件时调用。

    这主要用于记录你从 QQ 网关接收到的事件数量。

    .. versionadded:: 2.0

    :param event_type: 收到的来自 QQ 的事件类型，例如 ``READY``.
    :type event_type: :class:`str`

.. function:: on_socket_raw_receive(msg)

    在处理和解析消息之前从 WebSocket 完全接收到消息时调用。
    当收到完整的消息并且不以任何方式解析传递的数据时，始终调度此事件。

    这仅对获取 WebSocket 流和调试有用。

    这需要在 :class:`Client` 中设置 ``enable_debug_events`` 设置。

    .. note::

        这仅适用于从客户端 WebSocket 接收的消息。语音 WebSocket 不会触发此事件。

    :param msg: 从 WebSocket 传入的消息。
    :type msg: :class:`str`

.. function:: on_socket_raw_send(payload)

    在发送消息之前在 WebSocket 上完成发送操作时调用。传递的参数是发送到 WebSocket 的消息。

    这仅对获取 WebSocket 流和调试有用。

    这需要在 :class:`Client` 中设置 ``enable_debug_events`` 设置。

    .. note::

        这仅适用于从客户端 WebSocket 发送的消息。语音 WebSocket 不会触发此事件。

    :param payload: 即将传递到 WebSocket 库的消息。它可以是 :class:`bytes` 表示二进制消息或 :class:`str` 表示常规文本消息。

.. function:: on_audio_start(audio)

    音频开始播放时调用。

    这需要启用 :attr:`Intents.audio`。

    :param audio: 音频资料。
    :type message: :class:`AudioAction`

.. function:: on_audio_stop(audio)

    音频停止播放时调用。

    这需要启用 :attr:`Intents.audio`。

    :param audio: 音频资料。
    :type message: :class:`AudioAction`

.. function:: on_mic_start(audio)

    有人上麦时时调用。

    这需要启用 :attr:`Intents.audio`。

    :param audio: 音频资料。
    :type message: :class:`AudioAction`

.. function:: on_mic_stop(audio)

    有人下麦时时调用。

    这需要启用 :attr:`Intents.audio`。

    :param audio: 音频资料。
    :type message: :class:`AudioAction`

.. function:: on_message(message)

    在创建和发送 Message 时调用。

    这需要启用 :attr:`Intents.messages`。

    .. warning::

        你的机器人自己的消息通过此事件发送。
        这可能会导致“递归”的情况，具体取决于你的机器人的编程方式。
        如果你希望机器人不回复自己，请考虑检查用户 ID。注意 :class:`~ext.commands.Bot` 没有这个问题。

    :param message: 当前消息。
    :type message: :class:`Message`

.. function:: on_message_audit(audit)

    在消息审核通过或拒绝时调用。

    这需要启用 :attr:`Intents.audit`。

    :param audit: 当前消息审核。
    :type message: :class:`MessageAudit`

.. function:: on_guild_channel_delete(channel)
              on_guild_channel_create(channel)

    每当删除或创建子频道时调用。

    请注意，你可以从 :attr:`~abc.GuildChannel.guild` 获取频道。

    这需要启用 :attr:`Intents.guilds`。

    :param channel: 创建或删除的公会频道。
    :type channel: :class:`abc.GuildChannel`

.. function:: on_guild_channel_update(before, after)

    每当更新子频道时调用。 例如 更改名称。

    这需要启用 :attr:`Intents.guilds`。

    :param before: 更新公会频道的旧信息。
    :type before: :class:`abc.GuildChannel`
    :param after: 更新公会频道的新信息。
    :type after: :class:`abc.GuildChannel`


.. function:: on_member_join(member)
              on_member_remove(member)

    当 :class:`Member` 离开或加入 :class:`Guild` 时调用。

    这需要启用 :attr:`Intents.members`。

    :param member: 加入或离开的成员。
    :type member: :class:`Member`

.. function:: on_member_update(before, after)

    当 :class:`Member` 更新他们的个人资料时调用。

    这需要启用 :attr:`Intents.members`。

    :param before: 更新成员的旧信息。
    :type before: :class:`Member`
    :param after: 更新成员的新信息。
    :type after: :class:`Member`

.. function:: on_guild_join(guild)

    当 :class:`Guild` 由 :class:`Client` 创建或当:class:`Client` 加入公会时调用。

    这需要启用 :attr:`Intents.guilds`。

    :param guild: 加入的公会。
    :type guild: :class:`Guild`

.. function:: on_guild_remove(guild)

    当 :class:`Guild` 从 :class:`Client` 中移除时调用。

    这是通过但不限于以下情况发生的：
     - 客户端被踢了。
     - 客户端离开了公会。
     - 客户端或公会所有者删除了公会。

    为了调用这个事件，Client 必须是公会的一部分。 （即它是 :attr:`Client.guilds` 的一部分）

    这需要启用 :attr:`Intents.guilds`。

    :param guild: 被移除的公会。
    :type guild: :class:`Guild`

.. function:: on_guild_update(before, after)

    当 :class:`Guild` 更新时调用，例如：

     - 更名
     - 等等

    这需要启用 :attr:`Intents.guilds` 。

    :param before: 更新前的公会。
    :type before: :class:`Guild`
    :param after: 更新后的公会。
    :type after: :class:`Guild`

.. function:: on_reaction_add(reaction, user)

    当消息添加了反应时调用。类似于:func:`on_message_edit` ，如果在内部消息缓存中找不到该消息，则不会调用此事件。
    考虑使用 :func:`on_raw_reaction_add` 代替。

    .. note::

        要让 :class:`Message` 得到响应，请通过:attr:`Reaction.message` 访问它。

    这需要启用 :attr:`Intents.reactions` 。

    :param reaction: 反应的当前状态。
    :type reaction: :class:`Reaction`
    :param user: 添加反应的用户。
    :type user: Union[:class:`Member`, :class:`User`]

.. function:: on_raw_reaction_add(payload)

    当消息添加了反应时调用。与:func:`on_reaction_add` 不同，无论内部消息缓存的状态如何，都会调用它。

    这需要启用 :attr:`Intents.reactions`。

    :param payload: 原始事件负载数据。
    :type payload: :class:`RawReactionActionEvent`

.. function:: on_reaction_remove(reaction, user)

    当消息已删除反应时调用。与 :func:`on_message_edit` 类似，如果在内部消息缓存中找不到该消息，则不会调用此事件。

    .. note::

        要获得正在响应的消息，请通过:attr:`Reaction.message` 访问它。

    这需要同时启用 :attr:`Intents.reactions` 和 :attr:`Intents.members` 。

    :param reaction: 反应的当前状态。
    :type reaction: :class:`Reaction`
    :param user: 添加反应的用户。
    :type user: Union[:class:`Member`, :class:`User`]

.. function:: on_raw_reaction_remove(payload)

    当消息已删除反应时调用。与:func:`on_reaction_remove` 不同，无论内部消息缓存的状态如何，都会调用它。

    这需要启用 :attr:`Intents.reactions`。

    :param payload: 原始事件负载数据。
    :type payload: :class:`RawReactionActionEvent`

.. function:: on_reaction_clear(message, reactions)

    当一条消息的所有反应都被移除时调用。类似于:func:`on_message_edit` ，
    如果在内部消息缓存中找不到该消息，则不会调用此事件。考虑使用 :func:`on_raw_reaction_clear` 代替。

    这需要启用 :attr:`Intents.reactions` 。

    :param message: 已清除其反应的消息。
    :type message: :class:`Message`
    :param reactions: 被移除的反应。
    :type reactions: List[:class:`Reaction`]

.. function:: on_raw_reaction_clear(payload)

    当消息的所有反应都被删除时调用。与:func:`on_reaction_clear` 不同，无论内部消息缓存的状态如何，都会调用它。

    这需要启用 :attr:`Intents.reactions`。

    :param payload: 原始事件负载数据。
    :type payload: :class:`RawReactionClearEvent`

.. function:: on_reaction_clear_emoji(reaction)

    当消息已删除特定反应时调用。类似于:func:`on_message_edit`，如果在内部消息缓存中找不到该消息，则不会调用此事件。
    考虑使用 :func:`on_raw_reaction_clear_emoji` 代替。

    这需要启用 :attr:`Intents.reactions`。

    .. versionadded:: 1.3

    :param reaction: 得到清除的反应。
    :type reaction: :class:`Reaction`

.. function:: on_raw_reaction_clear_emoji(payload)

    当消息已删除特定反应时调用。与 :func:`on_reaction_clear_emoji` 不同，无论内部消息缓存的状态如何，它都会被调用。

    这需要启用 :attr:`Intents.reactions`。

    .. versionadded:: 1.3

    :param payload: 原始事件负载数据。
    :type payload: :class:`RawReactionClearEmojiEvent`

.. _qq-api-utils:

实用功能
-----------------

.. autofunction:: qq.utils.find

.. autofunction:: qq.utils.get

.. autofunction:: qq.utils.remove_markdown

.. autofunction:: qq.utils.escape_markdown

.. autofunction:: qq.utils.escape_mentions

.. autofunction:: qq.utils.sleep_until

.. autofunction:: qq.utils.utcnow

.. autofunction:: qq.utils.format_dt

.. _qq-api-enums:

枚举
-------------

API 为某些类型的字符串提供了一些枚举，以避免 API 被字符串类型化，以防将来字符串发生变化。
所有枚举都是内部类的子类，它模仿了 :class:`enum.Enum` 的行为。

.. class:: ChannelType

    指定频道的类型。

    .. attribute:: text

        一个文字频道。
    .. attribute:: voice

        一个语音通道。
    .. attribute:: category

        一个分类频道。
    .. attribute:: app

        一个应用频道。
    .. attribute:: thread

        一个论坛频道。
    .. attribute:: live

        一个直播频道。

.. class:: AudioStatusType

    音频的状态。

    .. attribute:: START

        开始播放操作。
    .. attribute:: PAUSE

        暂停播放操作。
    .. attribute:: RESUME

        继续播放操作。
    .. attribute:: STOP

        停止播放操作

异步迭代器
----------------

一些 API 函数返回一个“异步迭代器”。 异步迭代器是能够在 :ref:`async for 语句 <py:async for>` 中使用的东西。

这些异步迭代器可以按如下方式使用：::

    async for elem in await client.fetch_guilds():
        # do stuff with elem here

某些实用程序可以更轻松地使用异步迭代器，详情如下。

.. class:: AsyncIterator

    代表“AsyncIterator”概念。 请注意，不存在这样的类，它纯粹是抽象的。

    .. container:: operations

        .. describe:: async for x in y

            迭代异步迭代器的内容。


    .. method:: next()
        :async:

        |coro|

        如果可能，将迭代器推进 1。 如果没有找到更多的项目，那么这会引发 :exc:`NoMoreItems`。

    .. method:: get(**attrs)
        :async:

        |coro|

        类似于 :func:`utils.get` ，除了运行异步迭代器。

        获取名为 “Test” 的频道： ::

            guild = await await client.fetch_guilds().get(name='Test')

    .. method:: find(predicate)
        :async:

        |coro|

        类似于 :func:`utils.find`，除了运行异步迭代器。

        不像:func:`utils.find`，提供的检查函数可以是 |coroutine_link|_ 。

        :param predicate: 要使用的检查函数。 可能是 |coroutine_link|_ 。
        :return: 为检查函数返回“True”或“None”的第一个元素。

    .. method:: flatten()
        :async:

        |coro|

        将异步迭代器扁平化为一个包含所有元素的列表。

        :return: 异步迭代器中每个元素的列表。
        :rtype: list

    .. method:: chunk(max_size)

        将项目收集到最大给定大小的块中。
        另一个 :class:`AsyncIterator` 被返回，它将项目收集到给定大小的 :class:`list`\s 中。 最大块大小必须是正整数。

        .. warning::

            收集的最后一个块可能没有“max_size”那么大。

        :param max_size: 单个块的大小。
        :rtype: :class:`AsyncIterator`

    .. method:: map(func)

        这类似于内置的 :func:`map <py:map>` 函数。 另一个类：`AsyncIterator` 被返回，它在它迭代的每个元素上执行该函数。 这个函数可以是一个普通函数，也可以是一个 |coroutine_link|_。
        创建内容迭代器: ::

            def transform(guild):
                return guild.name

            async for content in await client.fetch_guilds().map(transform):
                guild_name = content

        :param func: 在每个元素上调用的函数。 可能是 |coroutine_link|_ 。
        :rtype: :class:`AsyncIterator`

    .. method:: filter(predicate)

        这类似于内置的 :func:`filter <py:filter>` 函数。 返回另一个 :class:`AsyncIterator` 过滤原始异步迭代器。
        该检查函数可以是常规函数或 |coroutine_link|_ 。
        获取非名为 'Test' 的频道： ::

            def predicate(guild):
                return guild.name == 'Test'

            async for elem in await client.fetch_guilds().filter(predicate):
                ...

        :param predicate: 调用每个元素的检查函数。 可能是 |coroutine_link|_。
        :rtype: :class:`AsyncIterator`

抽象基类
-----------------------

一个 :term:`抽象基类` (也被称为 ``abc``) 是模型可以继承以获取行为的类。
**抽象基类不应该被实例化**。
它们主要用于 :func:`isinstance` 和 :func:`issubclass`\。

GuildChannel
~~~~~~~~~~~~~

.. attributetable:: qq.abc.GuildChannel

.. autoclass:: qq.abc.GuildChannel()
    :members:

Messageable
~~~~~~~~~~~~

.. attributetable:: qq.abc.Messageable

.. autoclass:: qq.abc.Messageable()
    :members:


QQ 模型
---------------

模型是从 QQ 接收的类，并不打算由库的用户创建。

.. danger::

    下面列出的类 **不是由用户创建的** ，也是 **只读的** 。

    例如，这意味着你不应该创建自己的 :class:`User` 实例，也不应该自己修改 :class:`User` 实例。

    如果你想获得这些模型类实例中的一个，
    必须通过缓存，而一种常见的方法是通过 :func:`utils.find` 函数或
    从 :ref:`qq-api-events` 中指定的事件获取 。

.. note::

    这里几乎所有的类都定义了 :ref:`py:slots`，这意味着数据类不可能有动态属性。

ClientUser
~~~~~~~~~~~~

.. attributetable:: ClientUser

.. autoclass:: ClientUser()
    :members:
    :inherited-members:

User
~~~~~

.. attributetable:: User

.. autoclass:: User()
    :members:
    :inherited-members:

Attachment
~~~~~~~~~~~

.. attributetable:: Attachment

.. autoclass:: Attachment()
    :members:

Asset
~~~~~

.. attributetable:: Asset

.. autoclass:: Asset()
    :members:
    :inherited-members:

Message
~~~~~~~

.. attributetable:: Message

.. autoclass:: Message()
    :members:

MessageAudit
~~~~~~~

.. attributetable:: MessageAudit

.. autoclass:: MessageAudit()
    :members:

Guild
~~~~~~

.. attributetable:: Guild

.. autoclass:: Guild()
    :members:

Permission
~~~~~~

.. attributetable:: Permission

.. autoclass:: Permission()
    :members:

Member
~~~~~~

.. attributetable:: Member

.. autoclass:: Member()
    :members:
    :inherited-members:

Role
~~~~~

.. attributetable:: Role

.. autoclass:: Role()
    :members:

PartialMessageable
~~~~~~~~~~~~~~~~~~~~

.. attributetable:: PartialMessageable

.. autoclass:: PartialMessageable()
    :members:
    :inherited-members:

TextChannel
~~~~~~~~~~~~

.. attributetable:: TextChannel

.. autoclass:: TextChannel()
    :members:
    :inherited-members:

VoiceChannel
~~~~~~~~~~~~~

.. attributetable:: VoiceChannel

.. autoclass:: VoiceChannel()
    :members:
    :inherited-members:

CategoryChannel
~~~~~~~~~~~~~~~~~

.. attributetable:: CategoryChannel

.. autoclass:: CategoryChannel()
    :members:
    :inherited-members:

AppChannel
~~~~~~~~~~~~~~~~~

.. attributetable:: AppChannel

.. autoclass:: AppChannel()
    :members:
    :inherited-members:

LiveChannel
~~~~~~~~~~~~~~~~~

.. attributetable:: LiveChannel

.. autoclass:: LiveChannel()
    :members:
    :inherited-members:

ThreadChannel
~~~~~~~~~~~~~~~~~

.. attributetable:: ThreadChannel

.. autoclass:: ThreadChannel()
    :members:
    :inherited-members:

DMChannel
~~~~~~~~~

.. attributetable:: DMChannel

.. autoclass:: DMChannel()
    :members:
    :inherited-members:
    :exclude-members: history

    .. automethod:: history
        :async-for:

Schedule
~~~~~~~~
.. attributetable:: Schedule

.. autoclass:: Schedule()
    :members:
    :inherited-members:


.. _qq_api_data:

数据类
--------------

有些类只是为了数据容器，这里列出了它们。

与 :ref:`models <qq_api_models>` 不同，你可以自己创建其中的大部分，即使它们也可以用来保存属性。

这里几乎所有的类都定义了 :ref:`py:slots`，这意味着数据类不可能有动态属性。

这个规则的唯一例外是:class:`Object`，它考虑到了动态属性。


Object
~~~~~~~

.. attributetable:: Object

.. autoclass:: Object
    :members:

Ark
~~~~~~

.. attributetable:: Ark

.. autoclass:: Ark
    :members:

Embed
~~~~~~

.. attributetable:: Embed

.. autoclass:: Embed
    :members:

AllowedMentions
~~~~~~~~~~~~~~~~~

.. attributetable:: AllowedMentions

.. autoclass:: AllowedMentions
    :members:

MessageReference
~~~~~~~~~~~~~~~~~

.. attributetable:: MessageReference

.. autoclass:: MessageReference
    :members:

PartialMessage
~~~~~~~~~~~~~~~~~

.. attributetable:: PartialMessage

.. autoclass:: PartialMessage
    :members:

Intents
~~~~~~~~~~

.. attributetable:: Intents

.. autoclass:: Intents
    :members:


File
~~~~~

.. attributetable:: File

.. autoclass:: File
    :members:

Colour
~~~~~~

.. attributetable:: Colour

.. autoclass:: Colour
    :members:

Permissions
~~~~~~~~~~~~

.. attributetable:: Permissions

.. autoclass:: Permissions
    :members:

PermissionOverwrite
~~~~~~~~~~~~~~~~~~~~

.. attributetable:: PermissionOverwrite

.. autoclass:: PermissionOverwrite
    :members:

ShardInfo
~~~~~~~~~~~

.. attributetable:: ShardInfo

.. autoclass:: ShardInfo()
    :members:


错误
------------

库能够抛出以下异常。

.. autoexception:: QQException

.. autoexception:: ClientException

.. autoexception:: LoginFailure

.. autoexception:: NoMoreItems

.. autoexception:: HTTPException
    :members:

.. autoexception:: Forbidden

.. autoexception:: NotFound

.. autoexception:: QQServerError

.. autoexception:: InvalidData

.. autoexception:: InvalidArgument

.. autoexception:: GatewayNotFound

.. autoexception:: ConnectionClosed

异常层次结构
~~~~~~~~~~~~~~~~~~~~~

.. exception_hierarchy::

    - :exc:`Exception`
        - :exc:`QQException`
            - :exc:`ClientException`
                - :exc:`InvalidData`
                - :exc:`InvalidArgument`
                - :exc:`LoginFailure`
                - :exc:`ConnectionClosed`
            - :exc:`NoMoreItems`
            - :exc:`GatewayNotFound`
            - :exc:`HTTPException`
                - :exc:`Forbidden`
                - :exc:`NotFound`
                - :exc:`QQServerError`
