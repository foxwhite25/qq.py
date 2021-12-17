import qq


class MyClient(qq.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.role_message_id = 0  # 可以响应以添加删除身份组的消息的 ID。
        self.emoji_to_role = {
            qq.PartialEmoji(custom=False, id='🔴'): 0,  # 与 Unicode 表情符号 '🔴' 关联的身份组的 ID。
            qq.PartialEmoji(custom=False, id='🟡'): 0,  # 与 Unicode 表情符号 '🟡' 关联的身份组的 ID。
            qq.PartialEmoji(custom=True, id='0'): 0,  # 与表情符号 ID 0 关联的身份组 ID。
        }

    async def on_raw_reaction_add(self, payload: qq.RawReactionActionEvent):
        """根据反应表情给出一个身份组。"""
        # 确保用户正在响应的消息是我们关心的消息。
        if payload.message_id != self.role_message_id:
            return

        guild = self.get_guild(payload.guild_id)
        if guild is None:
            # 检查我们是否仍在频道中并且它已被缓存。
            return

        try:
            role_id = self.emoji_to_role[payload.emoji]
        except KeyError:
            # 如果表情符号不是我们关心的那个，那么也退出。
            return

        role = guild.get_role(role_id)
        if role is None:
            # 确保身份组仍然存在并且有效。
            return

        try:
            # 最后，添加身份组。
            await payload.member.add_roles(role)
        except qq.HTTPException:
            # 如果我们想在出现错误的情况下做某事，我们会在这里做。
            pass

    async def on_raw_reaction_remove(self, payload: qq.RawReactionActionEvent):
        """删除基于反应表情符号的身份组。"""
        # 确保用户正在响应的消息是我们关心的消息。
        if payload.message_id != self.role_message_id:
            return

        guild = self.get_guild(payload.guild_id)
        if guild is None:
            # 检查我们是否仍在频道中并且它已被缓存。
            return

        try:
            role_id = self.emoji_to_role[payload.emoji]
        except KeyError:
            # 如果表情符号不是我们关心的那个，那么也退出。
            return

        role = guild.get_role(role_id)
        if role is None:
            # 确保身份组仍然存在并且有效。
            return

        # `on_raw_reaction_remove` 的负载不提供 `.member`
        # 所以我们必须自己从有效载荷的`.user_id` 中获取成员。
        member = guild.get_member(payload.user_id)
        if member is None:
            # 确保该成员仍然存在并且有效。
            return

        try:
            # 最后，删除身份组。
            await member.remove_roles(role)
        except qq.HTTPException:
            # 如果我们想在出现错误的情况下做某事，我们会在这里做。
            pass


intents = qq.Intents.default()
intents.members = True

client = MyClient(intents=intents)
client.run('token')
