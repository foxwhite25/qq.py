<div align="center">

# QQ.py

[![GitHub issues](https://img.shields.io/github/issues/foxwhite25/qq.py?style=for-the-badge)](https://github.com/foxwhite25/qq.py/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/foxwhite25/qq.py?style=for-the-badge)](https://github.com/foxwhite25/qq.py/pulls)
[![PyPI - License](https://img.shields.io/pypi/l/qq.py?style=for-the-badge)](https://pypi.org/project/qq.py/)
[![PyPI - Status](https://img.shields.io/pypi/status/qq.py?style=for-the-badge)](https://pypi.org/project/qq.py/)
[![PyPI](https://img.shields.io/pypi/v/qq.py?style=for-the-badge)](https://pypi.org/project/qq.py/)
[![Documentation Status](https://readthedocs.org/projects/qqpy/badge/?version=latest&style=for-the-badge)](https://qqpy.readthedocs.io/zh_CN/latest/?badge=latest)

_✨ 用 Python 编写的用于 QQ频道机器人 的现代化、易于使用、功能丰富且异步的 API。 ✨_

</div>

## 主要特点

- 使用 ``async`` 和 ``await`` 的现代 Pythonic API。
- 优化速度和内存。

## 安装

**需要 Python 3.8或以上的版本**

要安装库，你只需运行以下命令：
```
pip3 install -U qq.py
```

## 快速示例
```python
from qq import *


class MyClient(Client):
    async def on_ready(self):
        print('使用', self.user, '登陆')

    async def on_message(self, message):
        # 不要回复自己
        if message.author == self.user:
            return

        if 'ping' in message.content:
            await message.channel.send('pong')


if __name__ == '__main__':
    client = MyClient(app_id='', token='')
    client.run()
```
当完成初始化输出当前机器人用户对象，收到带有 ``ping`` 的信息事件时发送 ``pong``

## 链接
* [文档](https://qqpy.readthedocs.io/zh_CN/latest/?badge=latest)
* [QQ API](https://bot.q.qq.com/wiki/develop/api/)
* 帮助 QQ 群 -583799186
