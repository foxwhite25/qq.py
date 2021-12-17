import random

import qq
from qq.ext import commands


class MyContext(commands.Context):
    async def tick(self, value):
        # 根据值是 True 还是 False 用表情符号对消息做出反应，如果它是 True，它会添加一个绿色复选标记否则，它会添加一个红十字标记
        emoji = '✔️' if value else '❌'
        try:
            # 这将对命令作者的消息做出反应
            await self.message.add_reaction(emoji)
        except qq.HTTPException:
            # 有时在此期间会发生错误，例如您可能没有权限这样做，我们不介意，所以我们可以忽略它们
            pass


class MyBot(commands.Bot):
    async def get_context(self, message, *, cls=MyContext):
        # 当您覆盖此方法时，您将新的 Context 子类传递给 super() 方法，该方法告诉机器人使用新的 MyContext 类
        return await super().get_context(message, cls=cls)


bot = MyBot(command_prefix='!')


@bot.command()
async def guess(ctx, number: int):
    """ 猜一个从 1 到 6 的随机数。 """
    # 在前面的例子中解释过，这会给你一个 1-6 的随机数
    value = random.randint(1, 6)
    # 使用新的辅助函数，如果猜测正确，您可以添加一个绿色勾，如果不正确，您可以添加一个红叉
    await ctx.tick(number == value)


# 重要提示：您不应该对您的令牌进行硬编码
# 这些非常重要，泄露它们会让人们用你的机器人做非常恶意的事情。
# 尝试使用文件或其他东西来保护它们的私密性，不要将其提交到 GitHub
token = "your token here"
bot.run(token)
