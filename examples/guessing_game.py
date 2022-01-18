import qq
import random
import asyncio


class MyClient(qq.Client):
    async def on_ready(self):
        print(f'以 {self.user} 身份登录（ID：{self.user.id}）')
        print('------')

    async def on_message(self, message):
        # 我们不希望机器人回复自己
        if message.author.id == self.user.id:
            return

        if message.content.startswith('$guess'):
            await message.channel.send('猜一个 1 到 10 之间的数字。')

            def is_correct(m):
                return m.author == message.author and m.content.isdigit()

            answer = random.randint(1, 10)

            try:
                guess = await self.wait_for('message', check=is_correct, timeout=5.0)
            except asyncio.TimeoutError:
                return await message.channel.send(f'抱歉，你花了太长时间，答案是{answer}。')

            if int(guess.content) == answer:
                await message.channel.send('你说对了！')
            else:
                await message.channel.send(f'哎呀。它实际上是{answer}。')


client = MyClient()
client.run('token')
