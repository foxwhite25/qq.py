import qq
import asyncio


class MyClient(qq.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 创建后台任务并在后台运行
        self.bg_task = self.loop.create_task(self.my_background_task())

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def my_background_task(self):
        await self.wait_until_ready()
        counter = 0
        channel = self.get_channel(1234567)  # 频道 ID 放在这里
        while not self.is_closed():
            counter += 1
            await channel.send(str(counter))
            await asyncio.sleep(60)  # 任务每 60 秒运行一次


client = MyClient()
client.run('token')
