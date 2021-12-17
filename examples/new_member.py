import qq


class MyClient(qq.Client):
    async def on_ready(self):
        print(f'以 {self.user} 身份登录（ID：{self.user.id}）')
        print('------')

    async def on_member_join(self, member: qq.Member):
        channel = member.guild.fetch_channel(114514)  # 频道ID
        if channel is not None:
            to_send = f'欢迎 {member.mention} 加入 {member.guild.name}！'
            await channel.send(to_send)


intents = qq.Intents.default()
intents.members = True

client = MyClient(intents=intents)
client.run('token')
