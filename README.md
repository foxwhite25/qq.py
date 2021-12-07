# QQ.py

用 Python 编写的用于 QQ频道机器人 现代化、易于使用、功能丰富(? 且异步的 API sdk。

## 主要特点

- 使用 ``async`` 和 ``await`` 的现代 Pythonic API。

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
        print('Logged on as', self.user)

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        if message.content == 'ping':
            await message.channel.send('pong')


if __name__ == '__main__':
    client = MyClient(app_id='', token='')
    client.run()
```
当完成初始化输出当前机器人用户对象

## 链接
* [QQ API](https://bot.q.qq.com/wiki/develop/api/)