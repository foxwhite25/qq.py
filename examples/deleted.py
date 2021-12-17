import qq

# 官方还不支持撤回
class MyClient(qq.Client):
    async def on_ready(self):
        print(f'以 {self.user} 身份登录（ID：{self.user.id}）')
        print('------')

    async def on_message(self, message):
        if message.content.startswith('!deleteme'):
            msg = await message.channel.send('我现在要撤回自己...')
            await msg.delete()

            # this also works
            await message.channel.send('3秒后再见……', delete_after=3.0)

    async def on_message_delete(self, message):
        msg = f'{message.author} 撤回了消息：{message.content}'
        await message.channel.send(msg)


client = MyClient()
client.run('token')
