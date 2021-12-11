:orphan:

.. _logging_setup:

设置日志
===================

*qq.py* 通过 python自带模块 :mod:`logging` 日志记录错误和调试信息 。
强烈建议配置logging模块，因为如果没有设置，将不会输出错误或警告。
``logging`` 模块的配置可以很简单::

    import logging

    logging.basicConfig(level=logging.INFO)

放置在应用程序的开头。这会将来自 qq 的日志以及其他使用 ``logging`` 模块的库直接输出到控制台。

可选的 ``Level`` 参数指定要记录的事件级别，并且可以是 ``CRITICAL``, ``ERROR``, ``WARNING``, ``INFO``, 和
``DEBUG`` 的任何一个如果未指定，则默认为 ``WARNING`` 。

使用 :mod:`logging` 模块可以进行更高级的设置。
例如，要将日志写入名为 ``qq.log`` 的文件而不是将它们输出到控制台，可以使用以下代码段::

    import qq
    import logging

    logger = logging.getLogger('qq')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='qq.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

建议这样做，尤其是在诸如 ``INFO`` 和 ``DEBUG`` 之类的详细级别，因为记录了大量事件并且会阻塞程序的标准输出。


有关更多信息，请查看 :mod:`logging` 模块的文档和教程。
