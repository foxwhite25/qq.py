import random

import qq
from qq.ext import commands

intents = qq.Intents.default()

bot = commands.Bot(command_prefix='?', intents=intents, owner_id=114514)  # 注册机器人前缀为 ?


@bot.event
async def on_ready():  # 注册 on_ready 事件
    print(f'以 {bot.user} 身份登录（ID：{bot.user.id}）')
    print('------')


@bot.command(name='早上好')
async def _gm(ctx):
    ran = ['1', '2', '3', '4']
    await ctx.reply(random.choice(ran))


@bot.command()
async def add(ctx, content: str):
    content = content.split('+')  # 将输入用 + 分开
    result = 0  # 初始化 result
    for num in content:  # 循环 content 里面的所有参数
        if num.isnumeric():  # 如果 参数是数字
            result += int(num)  # 加到 result里面
    await ctx.reply(result)  # 发送 result


@bot.command()
async def markdown(ctx: commands.Context, content: str):
    await ctx.send(markdown=qq.Markdown(content=content))
    data = {
        "text": [content],
    }
    await ctx.send(markdown=qq.Markdown().from_dict(template_id=1, data=data))


@bot.command()  # 注册指令 '?roll', 参数为 dice
async def roll(ctx, dice: str):
    """以 NdN 格式掷骰子。"""
    try:
        rolls, limit = map(int, dice.split('d'))  # 判断格式是不是 NdN
    except Exception:
        await ctx.reply('格式必须是 NdN！')
        return

    result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
    await ctx.reply(result)


@bot.command(description='当你有选择困难症')  # 注册指令 '?choose', 参数为多个choices， 例如 ?choose a b，choose会是['a', 'b']
async def choose(ctx, *choices: str):
    """在多个选项之间进行选择。"""
    audit_id = await ctx.reply(random.choice(choices))  # 发送从 List 中随机选择一个，

    # 因为用的是 send，而也没有附上 referece，所以是主动消息，因此返回的是 str 的 audit_id

    def audit_message(audit: qq.MessageAudit):  # 检测 audit 事件的 id 是否和获得的 id 一致
        return audit.id == audit_id

    audit = await bot.wait_for('message_audit', check=audit_message, timeout=60)  # 等待 message_audit 事件
    await ctx.reply("Audit passed" if audit.passed else "Audit failed")


@bot.command()  # 注册指令 '?repeat', 参数为 time content, content 默认值为 重复...
async def repeat(ctx, times: int, content='重复...'):
    """多次重复一条消息。"""
    for i in range(times):  # 重复 time 次
        await ctx.reply(content)  # 发送 content


@bot.group()
async def cool(ctx):
    """说用户是否很酷。

     实际上，这只是检查是否正在调用子命令。
    """
    if ctx.invoked_subcommand is None:
        await ctx.reply(f'不，{ctx.subcommand_passed} 不牛逼')


@cool.command(name='bot')
async def _bot(ctx):
    """机器人牛逼吗？"""
    await ctx.reply('是的，机器人很牛逼。')


@bot.command()
async def ark(ctx, count: int, *, anything: str):
    ark = qq.Ark(template_id=23)
    ark.set_attribute(key='#DESC#', value='aba')
    ark.set_attribute(key='#PROMPT#', value='aba')
    for _ in range(count):
        ark.add_field(desc=anything)
    await ctx.reply(ark=ark)


bot.run('token')
