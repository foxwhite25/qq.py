.. currentmodule:: qq

API 参考
===============

以下部分概述了 qq.py 的命令扩展模块的 API。

.. _ext_commands_api_bot:

机器人
------

Bot
~~~~

.. attributetable:: qq.ext.commands.Bot

.. autoclass:: qq.ext.commands.Bot
    :members:
    :inherited-members:
    :exclude-members: after_invoke, before_invoke, check, check_once, command, event, group, listen

    .. automethod:: Bot.after_invoke()
        :decorator:

    .. automethod:: Bot.before_invoke()
        :decorator:

    .. automethod:: Bot.check()
        :decorator:

    .. automethod:: Bot.check_once()
        :decorator:

    .. automethod:: Bot.command(*args, **kwargs)
        :decorator:
    
    .. automethod:: Bot.event()
        :decorator:

    .. automethod:: Bot.group(*args, **kwargs)
        :decorator:

    .. automethod:: Bot.listen(name=None)
        :decorator:

AutoShardedBot
~~~~~~~~~~~~~~~~

.. attributetable:: qq.ext.commands.AutoShardedBot

.. autoclass:: qq.ext.commands.AutoShardedBot
    :members:

前缀助手
----------------

.. autofunction:: qq.ext.commands.when_mentioned

.. autofunction:: qq.ext.commands.when_mentioned_or

.. _ext_commands_api_events:

事件参考
-----------------

这些事件的功能类似于 :ref:`常规事件<qq-api-events>`，但是它们来自命令扩展模块。

.. function:: qq.ext.commands.on_command_error(ctx, error)

    一个错误处理程序，当在命令中通过用户输入错误、检查失败或您自己的代码中的错误引发错误时调用。

    A default one is provided (:meth:`.Bot.on_command_error`).

    :param ctx: 调用 context。
    :type ctx: :class:`.Context`
    :param error: 引发的错误。
    :type error: :class:`.CommandError` derived

.. function:: qq.ext.commands.on_command(ctx)

    在找到命令并即将被调用时调用的事件。

    无论命令本身是通过错误成功还是完成，都会调用此事件。

    :param ctx: 调用 context。
    :type ctx: :class:`.Context`

.. function:: qq.ext.commands.on_command_completion(ctx)

    当命令完成其调用时调用的事件。

    仅当命令成功时才调用此事件，即所有检查均已通过且用户正确输入。

    :param ctx: 调用 context。
    :type ctx: :class:`.Context`

.. _ext_commands_api_command:

命令
----------

装饰器
~~~~~~~~~~~~

.. autofunction:: qq.ext.commands.command
    :decorator:

.. autofunction:: qq.ext.commands.group
    :decorator:

命令
~~~~~~~~~

.. attributetable:: qq.ext.commands.Command

.. autoclass:: qq.ext.commands.Command
    :members:
    :special-members: __call__
    :exclude-members: after_invoke, before_invoke, error

    .. automethod:: Command.after_invoke()
        :decorator:

    .. automethod:: Command.before_invoke()
        :decorator:

    .. automethod:: Command.error()
        :decorator:

命令组
~~~~~~

.. attributetable:: qq.ext.commands.Group

.. autoclass:: qq.ext.commands.Group
    :members:
    :inherited-members:
    :exclude-members: after_invoke, before_invoke, command, error, group

    .. automethod:: Group.after_invoke()
        :decorator:

    .. automethod:: Group.before_invoke()
        :decorator:

    .. automethod:: Group.command(*args, **kwargs)
        :decorator:

    .. automethod:: Group.error()
        :decorator:

    .. automethod:: Group.group(*args, **kwargs)
        :decorator:

命令组 Mixin
~~~~~~~~~~~

.. attributetable:: qq.ext.commands.GroupMixin

.. autoclass:: qq.ext.commands.GroupMixin
    :members:
    :exclude-members: command, group

    .. automethod:: GroupMixin.command(*args, **kwargs)
        :decorator:

    .. automethod:: GroupMixin.group(*args, **kwargs)
        :decorator:

.. _ext_commands_api_cogs:

齿轮
------

Cog
~~~~

.. attributetable:: qq.ext.commands.Cog

.. autoclass:: qq.ext.commands.Cog
    :members:

CogMeta
~~~~~~~~

.. attributetable:: qq.ext.commands.CogMeta

.. autoclass:: qq.ext.commands.CogMeta
    :members:

.. _ext_commands_help_command:

帮助命令
---------------

HelpCommand
~~~~~~~~~~~~

.. attributetable:: qq.ext.commands.HelpCommand

.. autoclass:: qq.ext.commands.HelpCommand
    :members:

默认帮助命令
~~~~~~~~~~~~~~~~~~~

.. attributetable:: qq.ext.commands.DefaultHelpCommand

.. autoclass:: qq.ext.commands.DefaultHelpCommand
    :members:
    :exclude-members: send_bot_help, send_cog_help, send_group_help, send_command_help, prepare_help_command

最小帮助命令
~~~~~~~~~~~~~~~~~~~

.. attributetable:: qq.ext.commands.MinimalHelpCommand

.. autoclass:: qq.ext.commands.MinimalHelpCommand
    :members:
    :exclude-members: send_bot_help, send_cog_help, send_group_help, send_command_help, prepare_help_command

分页器
~~~~~~~~~~

.. attributetable:: qq.ext.commands.Paginator

.. autoclass:: qq.ext.commands.Paginator
    :members:

枚举
------

.. class:: BucketType
    :module: qq.ext.commands

    Specifies a type of bucket for, e.g. a cooldown.

    .. attribute:: default

        The default bucket operates on a global basis.
    .. attribute:: user

        The user bucket operates on a per-user basis.
    .. attribute:: guild

        The guild bucket operates on a per-guild basis.
    .. attribute:: channel

        The channel bucket operates on a per-channel basis.
    .. attribute:: member

        The member bucket operates on a per-member basis.
    .. attribute:: category

        The category bucket operates on a per-category basis.
    .. attribute:: role

        The role bucket operates on a per-role basis.

        .. versionadded:: 1.3


.. _ext_commands_api_checks:

检查
-------

.. autofunction:: qq.ext.commands.check(predicate)
    :decorator:

.. autofunction:: qq.ext.commands.check_any(*checks)
    :decorator:

.. autofunction:: qq.ext.commands.has_role(item)
    :decorator:

.. autofunction:: qq.ext.commands.has_any_role(*items)
    :decorator:

.. autofunction:: qq.ext.commands.bot_has_role(item)
    :decorator:

.. autofunction:: qq.ext.commands.bot_has_any_role(*items)
    :decorator:

.. autofunction:: qq.ext.commands.cooldown(rate, per, type=qq.ext.commands.BucketType.default)
    :decorator:

.. autofunction:: qq.ext.commands.dynamic_cooldown(cooldown, type=BucketType.default)
    :decorator:

.. autofunction:: qq.ext.commands.max_concurrency(number, per=qq.ext.commands.BucketType.default, *, wait=False)
    :decorator:

.. autofunction:: qq.ext.commands.before_invoke(coro)
    :decorator:

.. autofunction:: qq.ext.commands.after_invoke(coro)
    :decorator:

.. autofunction:: qq.ext.commands.guild_only(,)
    :decorator:

.. autofunction:: qq.ext.commands.dm_only(,)
    :decorator:

.. autofunction:: qq.ext.commands.is_owner(,)
    :decorator:

.. _ext_commands_api_context:

冷却
---------

.. attributetable:: qq.ext.commands.Cooldown

.. autoclass:: qq.ext.commands.Cooldown
    :members:

Context
--------

.. attributetable:: qq.ext.commands.Context

.. autoclass:: qq.ext.commands.Context
    :members:
    :inherited-members:

.. _ext_commands_api_converters:

转换器
------------

.. autoclass:: qq.ext.commands.Converter
    :members:

.. autoclass:: qq.ext.commands.ObjectConverter
    :members:

.. autoclass:: qq.ext.commands.MemberConverter
    :members:

.. autoclass:: qq.ext.commands.UserConverter
    :members:

.. autoclass:: qq.ext.commands.MessageConverter
    :members:

.. autoclass:: qq.ext.commands.PartialMessageConverter
    :members:

.. autoclass:: qq.ext.commands.GuildChannelConverter
    :members:

.. autoclass:: qq.ext.commands.TextChannelConverter
    :members:

.. autoclass:: qq.ext.commands.VoiceChannelConverter
    :members:

.. autoclass:: qq.ext.commands.CategoryChannelConverter
    :members:

.. autoclass:: qq.ext.commands.ThreadChannelConverter
    :members:

.. autoclass:: qq.ext.commands.LiveChannelConverter
    :members:

.. autoclass:: qq.ext.commands.AppChannelConverter
    :members:

.. autoclass:: qq.ext.commands.InviteConverter
    :members:

.. autoclass:: qq.ext.commands.GuildConverter
    :members:

.. autoclass:: qq.ext.commands.RoleConverter
    :members:

.. autoclass:: qq.ext.commands.ColourConverter
    :members:

.. autoclass:: qq.ext.commands.GuildStickerConverter
    :members:

.. autoclass:: qq.ext.commands.clean_content
    :members:

.. autoclass:: qq.ext.commands.Greedy()

.. autofunction:: qq.ext.commands.run_converters

标志转换器
~~~~~~~~~~~~~~~

.. autoclass:: qq.ext.commands.FlagConverter
    :members:

.. autoclass:: qq.ext.commands.Flag()
    :members:

.. autofunction:: qq.ext.commands.flag

.. _ext_commands_api_errors:

错误
-----------

.. autoexception:: qq.ext.commands.CommandError
    :members:

.. autoexception:: qq.ext.commands.ConversionError
    :members:

.. autoexception:: qq.ext.commands.MissingRequiredArgument
    :members:

.. autoexception:: qq.ext.commands.ArgumentParsingError
    :members:

.. autoexception:: qq.ext.commands.UnexpectedQuoteError
    :members:

.. autoexception:: qq.ext.commands.InvalidEndOfQuotedStringError
    :members:

.. autoexception:: qq.ext.commands.ExpectedClosingQuoteError
    :members:

.. autoexception:: qq.ext.commands.BadArgument
    :members:

.. autoexception:: qq.ext.commands.BadUnionArgument
    :members:

.. autoexception:: qq.ext.commands.BadLiteralArgument
    :members:

.. autoexception:: qq.ext.commands.PrivateMessageOnly
    :members:

.. autoexception:: qq.ext.commands.NoPrivateMessage
    :members:

.. autoexception:: qq.ext.commands.CheckFailure
    :members:

.. autoexception:: qq.ext.commands.CheckAnyFailure
    :members:

.. autoexception:: qq.ext.commands.CommandNotFound
    :members:

.. autoexception:: qq.ext.commands.DisabledCommand
    :members:

.. autoexception:: qq.ext.commands.CommandInvokeError
    :members:

.. autoexception:: qq.ext.commands.TooManyArguments
    :members:

.. autoexception:: qq.ext.commands.UserInputError
    :members:

.. autoexception:: qq.ext.commands.CommandOnCooldown
    :members:

.. autoexception:: qq.ext.commands.MaxConcurrencyReached
    :members:

.. autoexception:: qq.ext.commands.NotOwner
    :members:

.. autoexception:: qq.ext.commands.MessageNotFound
    :members:

.. autoexception:: qq.ext.commands.MemberNotFound
    :members:

.. autoexception:: qq.ext.commands.GuildNotFound
    :members:

.. autoexception:: qq.ext.commands.UserNotFound
    :members:

.. autoexception:: qq.ext.commands.ChannelNotFound
    :members:

.. autoexception:: qq.ext.commands.ChannelNotReadable
    :members:

.. autoexception:: qq.ext.commands.ThreadNotFound
    :members:

.. autoexception:: qq.ext.commands.BadColourArgument
    :members:

.. autoexception:: qq.ext.commands.RoleNotFound
    :members:

.. autoexception:: qq.ext.commands.BadInviteArgument
    :members:

.. autoexception:: qq.ext.commands.EmojiNotFound
    :members:

.. autoexception:: qq.ext.commands.PartialEmojiConversionFailure
    :members:

.. autoexception:: qq.ext.commands.GuildStickerNotFound
    :members:

.. autoexception:: qq.ext.commands.BadBoolArgument
    :members:

.. autoexception:: qq.ext.commands.MissingPermissions
    :members:

.. autoexception:: qq.ext.commands.BotMissingPermissions
    :members:

.. autoexception:: qq.ext.commands.MissingRole
    :members:

.. autoexception:: qq.ext.commands.BotMissingRole
    :members:

.. autoexception:: qq.ext.commands.MissingAnyRole
    :members:

.. autoexception:: qq.ext.commands.BotMissingAnyRole
    :members:

.. autoexception:: qq.ext.commands.NSFWChannelRequired
    :members:

.. autoexception:: qq.ext.commands.FlagError
    :members:

.. autoexception:: qq.ext.commands.BadFlagArgument
    :members:

.. autoexception:: qq.ext.commands.MissingFlagArgument
    :members:

.. autoexception:: qq.ext.commands.TooManyFlags
    :members:

.. autoexception:: qq.ext.commands.MissingRequiredFlag
    :members:

.. autoexception:: qq.ext.commands.ExtensionError
    :members:

.. autoexception:: qq.ext.commands.ExtensionAlreadyLoaded
    :members:

.. autoexception:: qq.ext.commands.ExtensionNotLoaded
    :members:

.. autoexception:: qq.ext.commands.NoEntryPointError
    :members:

.. autoexception:: qq.ext.commands.ExtensionFailed
    :members:

.. autoexception:: qq.ext.commands.ExtensionNotFound
    :members:

.. autoexception:: qq.ext.commands.CommandRegistrationError
    :members:


Exception Hierarchy
~~~~~~~~~~~~~~~~~~~~~

.. exception_hierarchy::

    - :exc:`~.qqException`
        - :exc:`~.commands.CommandError`
            - :exc:`~.commands.ConversionError`
            - :exc:`~.commands.UserInputError`
                - :exc:`~.commands.MissingRequiredArgument`
                - :exc:`~.commands.TooManyArguments`
                - :exc:`~.commands.BadArgument`
                    - :exc:`~.commands.MessageNotFound`
                    - :exc:`~.commands.MemberNotFound`
                    - :exc:`~.commands.GuildNotFound`
                    - :exc:`~.commands.UserNotFound`
                    - :exc:`~.commands.ChannelNotFound`
                    - :exc:`~.commands.ChannelNotReadable`
                    - :exc:`~.commands.BadColourArgument`
                    - :exc:`~.commands.RoleNotFound`
                    - :exc:`~.commands.BadInviteArgument`
                    - :exc:`~.commands.EmojiNotFound`
                    - :exc:`~.commands.GuildStickerNotFound`
                    - :exc:`~.commands.PartialEmojiConversionFailure`
                    - :exc:`~.commands.BadBoolArgument`
                    - :exc:`~.commands.ThreadNotFound`
                    - :exc:`~.commands.FlagError`
                        - :exc:`~.commands.BadFlagArgument`
                        - :exc:`~.commands.MissingFlagArgument`
                        - :exc:`~.commands.TooManyFlags`
                        - :exc:`~.commands.MissingRequiredFlag`
                - :exc:`~.commands.BadUnionArgument`
                - :exc:`~.commands.BadLiteralArgument`
                - :exc:`~.commands.ArgumentParsingError`
                    - :exc:`~.commands.UnexpectedQuoteError`
                    - :exc:`~.commands.InvalidEndOfQuotedStringError`
                    - :exc:`~.commands.ExpectedClosingQuoteError`
            - :exc:`~.commands.CommandNotFound`
            - :exc:`~.commands.CheckFailure`
                - :exc:`~.commands.CheckAnyFailure`
                - :exc:`~.commands.PrivateMessageOnly`
                - :exc:`~.commands.NoPrivateMessage`
                - :exc:`~.commands.NotOwner`
                - :exc:`~.commands.MissingPermissions`
                - :exc:`~.commands.BotMissingPermissions`
                - :exc:`~.commands.MissingRole`
                - :exc:`~.commands.BotMissingRole`
                - :exc:`~.commands.MissingAnyRole`
                - :exc:`~.commands.BotMissingAnyRole`
                - :exc:`~.commands.NSFWChannelRequired`
            - :exc:`~.commands.DisabledCommand`
            - :exc:`~.commands.CommandInvokeError`
            - :exc:`~.commands.CommandOnCooldown`
            - :exc:`~.commands.MaxConcurrencyReached`
        - :exc:`~.commands.ExtensionError`
            - :exc:`~.commands.ExtensionAlreadyLoaded`
            - :exc:`~.commands.ExtensionNotLoaded`
            - :exc:`~.commands.NoEntryPointError`
            - :exc:`~.commands.ExtensionFailed`
            - :exc:`~.commands.ExtensionNotFound`
    - :exc:`~.ClientException`
        - :exc:`~.commands.CommandRegistrationError`
