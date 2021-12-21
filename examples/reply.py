import qq


class MyClient(qq.Client):
    async def on_ready(self):
        print(f'以 {self.user} 身份登录（ID：{self.user.id}）')
        print('------')

    async def on_message(self, message):
        # 我们不希望机器人回复自己
        if message.author.id == self.user.id:
            return

        if message.content.startswith('!hello'):
            await message.reply('你好!', mention_author=message.author)


client = MyClient()
client.run('token')
