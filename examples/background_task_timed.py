import datetime

import qq
from qq.ext import tasks

times = [datetime.time(hour=t, minute=m) for t in list(range(1, 13)) for m in list(range(0, 60))]


class MyClient(qq.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 一个我们可以从我们的任务中访问的属性
        self.counter = 0

        # 启动任务在后台运行
        self.my_background_task.start()

    async def on_ready(self):
        print(f'以 {self.user} 身份登录（ID：{self.user.id}）')
        print('------')

    @tasks.loop(time=times)  # 任务每 60 秒运行一次
    async def my_background_task(self):
        # channel = self.get_channel(1612581)  # 子频道 ID 放在这里
        # self.counter += 1
        # await channel.send(str(self.counter))
        print(1)

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # 等待机器人登录


client = MyClient()
client.run('token')