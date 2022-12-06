<div align="center">

![[object Object]](https://socialify.git.ci/foxwhite25/qq.py/image?description=1&font=Source%20Code%20Pro&forks=1&issues=1&language=1&name=1&owner=1&stargazers=1&theme=Auto)

[![PyPI - License](https://img.shields.io/pypi/l/qq.py?style=for-the-badge)](https://pypi.org/project/qq.py/)
[![PyPI - Status](https://img.shields.io/pypi/status/qq.py?style=for-the-badge)](https://pypi.org/project/qq.py/)
[![PyPI](https://img.shields.io/pypi/v/qq.py?style=for-the-badge)](https://pypi.org/project/qq.py/)
[![Documentation Status](https://readthedocs.org/projects/qqpy/badge/?version=latest&style=for-the-badge)](https://qqpy.readthedocs.io/zh_CN/latest/?badge=latest)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/qq.py?style=for-the-badge)](https://pypi.org/project/qq.py/)

_✨ 用 Python 编写的用于 QQ频道机器人 的现代化、易于使用、功能丰富且异步的 API。 ✨_

</div>

## 主要特点

- 使用 ``async`` 和 ``await`` 的现代 Pythonic API。
- 优化速度和内存。

## 安装

**需要 Python 3.8或以上的版本** 和一根接入互联网的网线。

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
    client = MyClient()
    client.run(token='app_id.token')
```

### Bot 示例
````python
import qq
from qq.ext import commands

bot = commands.Bot(command_prefix='>', owner_id='你的用户ID') # owner_id 是 int 类型

@bot.event
async def on_ready():
    print(f'以 {bot.user} 身份登录（ID：{bot.user.id}）')
    print('------')

@bot.command()
async def ping(ctx):
    await ctx.send('pong')

bot.run('app_id.token')
````

你可以在 example 目录中找到更多示例。

## 链接
* [文档](https://qqpy.readthedocs.io/zh_CN/latest/?badge=latest)
* [QQ API](https://bot.q.qq.com/wiki/develop/api/)
* [帮助 QQ 群 - 583799186](https://qm.qq.com/cgi-bin/qm/qr?k=5BuK-ZVjbNxVmfdobpeLyeo_xPbsQcKz&jump_from=webapi)
* [非官方 Discord 服务器](https://discord.gg/YkBykQKqhb)
