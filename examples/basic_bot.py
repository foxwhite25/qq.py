import qq
from qq.ext import commands
import random

intents = qq.Intents.default()

bot = commands.Bot(command_prefix='?', description=description, intents=intents)


@bot.event
async def on_ready():
    print(f'以 {bot.user} 身份登录（ID：{bot.user.id}）')
    print('------')


@bot.command()
async def add(ctx, left: int, right: int):
    """将两个数字相加。"""
    await ctx.send(left + right)


@bot.command()
async def roll(ctx, dice: str):
    """以 NdN 格式掷骰子。"""
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await ctx.send('格式必须是 NdN！')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await ctx.send(result)


@bot.command(description='当你有选择困难症')
async def choose(ctx, *choices: str):
    """在多个选项之间进行选择。"""
    await ctx.send(random.choice(choices))


@bot.command()
async def repeat(ctx, times: int, content='重复...'):
    """多次重复一条消息。"""
    for i in range(times):
        await ctx.send(content)


@bot.command()
async def joined(ctx, member: qq.Member):
    """当成员加入。"""
    await ctx.send(f'{member.name} 加入')


@bot.group()
async def cool(ctx):
    """说用户是否很酷。

     实际上，这只是检查是否正在调用子命令。
    """
    if ctx.invoked_subcommand is None:
        await ctx.send(f'不，{ctx.subcommand_passed} 不牛逼')


@cool.command(name='bot')
async def _bot(ctx):
    """机器人牛逼吗？"""
    await ctx.send('是的，机器人很牛逼。')


bot.run('token')
