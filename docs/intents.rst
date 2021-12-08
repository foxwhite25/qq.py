:orphan:

.. currentmodule:: discord
.. versionadded:: 1.5
.. _intents_primer:

网关Intents入门
=============================

:class:`Intents` 的简介。意图基本上允许机器人订阅特定的事件桶。对应于每个 intent 的事件记录在 :class:`Intents` 对象的各个属性中。

这些`intents` 参数会被传递给 :class:`Client` 或其子类 (:class:`AutoShardedClient`, :class:`~.AutoShardedBot`, :class:`~.Bot`) 的构造函。

如果未传递意图，则库默认启用除需要申请的 Intent 之外的每个 Intent，目前是除了 :attr:`Intents.audio` ， :attr:`Intents.direct_messages`，:attr:`Intents.messages`。

需要什么Intents？
--------------------------

您的机器人所需的意图只能由您自己决定。 :class:`Intents` 类中的每个属性都记录了它对应的 :ref:`events <qq-api-events>` 以及它启用的缓存类型。

例如，如果您想要一个没有Guild事件的机器人，那么我们可以执行以下操作：

.. code-block:: python3
   :emphasize-lines: 7,9,10

    import qq
    intents = qq.Intents.default()
    intents.guilds = False

    # 其他地方:
    # client = qq.Client(intents=intents)
    # or
    # from qq.ext import commands
    # bot = commands.Bot(command_prefix='!', intents=intents)

请注意，这不会启用 :attr:`Intents.audio`，因为它是一个需要申请的意图。

另一个示例显示一个仅处理 ``Message`` 和 ``Guild`` 信息的机器人：

.. code-block:: python3
   :emphasize-lines: 7,9,10

    import qq
    intents = qq.Intents(messages=True, guilds=True)

    # 其他地方:
    # client = qq.Client(intents=intents)
    # or
    # from qq.ext import commands
    # bot = commands.Bot(command_prefix='!', intents=intents)

.. _privileged_intents:

特权 Intent
---------------------

随着 API 要求机器人作者指定意图，一些意图受到进一步限制，需要更多的手动步骤。这些意图被称为需要申请的意图。

需要申请的意图是一种需要您转到开发人员频道并手动申请的意图。

.. note::

    即使您通过到开发人员频道启用意图，您仍然必须通过代码启用意图。