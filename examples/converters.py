import typing

import qq
from qq.ext import commands

intents = qq.Intents.default()
intents.members = True

bot = commands.Bot('!', intents=intents)


@bot.command()
async def userinfo(ctx: commands.Context, user: qq.User):
    # 在上面的命令签名中，您可以看到 `user` 参数被类型提示为 `qq.User`。 
    # 这意味着在命令调用期间，我们将尝试将作为 `user` 传递的值转换为 `qq.User` 实例。 
    # 文档说明了可以转换的内容，在 `qq.User` 的情况下，您传递一个 ID、提及或用户名例如 80088516616269824，@Danny 或 Danny
    # 
    # 注意：typehinting 仅在 `commands` 框架内充当转换器。 在标准 Python 中，它用于文档和 IDE 辅助目的。
    # 如果转换成功，我们将有一个 `qq.User` 实例，可以执行以下操作：
    user_id = user.id
    username = user.name
    avatar = user.avatar.url
    await ctx.send(f'找到的用户：{user_id} -- {username}\n{avatar}')


@userinfo.error
async def userinfo_error(ctx: commands.Context, error: commands.CommandError):
    # 如果上述转换因任何原因失败，它将引发 `commands.BadArgument`
    # 所以我们在这个错误处理程序中处理这个：
    if isinstance(error, commands.BadArgument):
        return await ctx.send('找不到该用户。')


# 自定义转换器在这里
class ChannelOrMemberConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        # 在这个例子中，我们制作了一个自定义转换器。
        # 这会检查输入是否可以通过使用库提供的预制转换器转换为 `qq.Member` 或 `qq.TextChannel` 实例。

        member_converter = commands.MemberConverter()
        try:
            # 尝试转换为 Member 实例。
            # 如果失败，则会引发异常。
            # 否则，我们只返回转换后的成员值。
            member = await member_converter.convert(ctx, argument)
        except commands.MemberNotFound:
            pass
        else:
            return member

        # 对 TextChannel 执行相同操作...
        textchannel_converter = commands.TextChannelConverter()
        try:
            channel = await textchannel_converter.convert(ctx, argument)
        except commands.ChannelNotFound:
            pass
        else:
            return channel

        # 如果该值无法转换，我们可以引发错误
        # 所以我们的错误处理程序可以在一个地方处理它。
        # 错误必须是 CommandError 派生的，所以 BadArgument 在这里工作正常。
        raise commands.BadArgument(f'没有成员或 TextChannel 可以从“{argument}”转换')


@bot.command()
async def notify(ctx: commands.Context, target: ChannelOrMemberConverter):
    # 这个命令签名使用了上面写的自定义转换器 在命令调用期间会发生的是，
    # 上面的 `target` 将被传递给 `ChannelOrMemberConverter.convert`
    # 方法的 `argument` 参数，并且转换将通过那里定义的过程。

    await target.send(f'{target.name} 你好!')


@bot.command()
async def ignore(ctx: commands.Context, target: typing.Union[qq.Member, qq.TextChannel]):
    # 这个命令签名使用了 `typing.Union` 类型提示。
    # `commands` 框架尝试按 **顺序** 转换此 Union 中的每种类型。
    # 因此，它会尝试将传递给 `target` 的任何内容转换为 `qq.Member` 实例。
    # 如果失败，它将尝试将其转换为 `qq.TextChannel` 实例。
    # 参见 : https://qqpy.readthedocs.io/zh_CN/latest/ext/commands/commands.html#typing-union
    # 注意：如果联合类型提示转换器失败，它将引发 `commands.BadUnionArgument` 而不是 `commands.BadArgument`。

    # 为了检查结果类型，使用`isinstance`
    if isinstance(target, qq.Member):
        await ctx.send(f'成员找到：{target.mention}，将它们添加到忽略列表中。')
    elif isinstance(target, qq.TextChannel):  # 这可以是一个“else”，但为了完整起见使用了 "elif"。
        await ctx.send(f'频道找到：{target.mention}，将其添加到忽略列表中。')


# 内置类型转换器。
@bot.command()
async def multiply(ctx: commands.Context, number: int, maybe: bool):
    # 我们在这里需要一个 `int` 和一个 `bool` 参数。
    # `bool` 是一个稍微特殊的情况，如下所示：
    # 参见: https://qqpy.readthedocs.io/zh_CN/latest/ext/commands/commands.html#bool

    if maybe is True:
        return await ctx.send(number * 2)
    await ctx.send(number * 5)


bot.run('token')
