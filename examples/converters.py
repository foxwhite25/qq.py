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
        # In this example we have made a custom converter.
        # This checks if an input is convertible to a
        # `qq.Member` or `qq.TextChannel` instance from the
        # input the user has given us using the pre-existing converters
        # that the library provides.

        member_converter = commands.MemberConverter()
        try:
            # Try and convert to a Member instance.
            # If this fails, then an exception is raised.
            # Otherwise, we just return the converted member value.
            member = await member_converter.convert(ctx, argument)
        except commands.MemberNotFound:
            pass
        else:
            return member

        # Do the same for TextChannel...
        textchannel_converter = commands.TextChannelConverter()
        try:
            channel = await textchannel_converter.convert(ctx, argument)
        except commands.ChannelNotFound:
            pass
        else:
            return channel

        # If the value could not be converted we can raise an error
        # so our error handlers can deal with it in one place.
        # The error has to be CommandError derived, so BadArgument works fine here.
        raise commands.BadArgument(f'No Member or TextChannel could be converted from "{argument}"')


@bot.command()
async def notify(ctx: commands.Context, target: ChannelOrMemberConverter):
    # This command signature utilises the custom converter written above
    # What will happen during command invocation is that the `target` above will be passed to
    # the `argument` parameter of the `ChannelOrMemberConverter.convert` method and 
    # the conversion will go through the process defined there.

    await target.send(f'Hello, {target.name}!')


@bot.command()
async def ignore(ctx: commands.Context, target: typing.Union[qq.Member, qq.TextChannel]):
    # This command signature utilises the `typing.Union` typehint.
    # The `commands` framework attempts a conversion of each type in this Union *in order*.
    # So, it will attempt to convert whatever is passed to `target` to a `qq.Member` instance.
    # If that fails, it will attempt to convert it to a `qq.TextChannel` instance.
    # See: https://qqpy.readthedocs.io/zh_CN/latest/ext/commands/commands.html#typing-union
    # NOTE: If a Union typehint converter fails it will raise `commands.BadUnionArgument`
    # instead of `commands.BadArgument`.

    # To check the resulting type, `isinstance` is used
    if isinstance(target, qq.Member):
        await ctx.send(f'Member found: {target.mention}, adding them to the ignore list.')
    elif isinstance(target, qq.TextChannel):  # this could be an `else` but for completeness' sake.
        await ctx.send(f'Channel found: {target.mention}, adding it to the ignore list.')


# Built-in type converters.
@bot.command()
async def multiply(ctx: commands.Context, number: int, maybe: bool):
    # We want an `int` and a `bool` parameter here.
    # `bool` is a slightly special case, as shown here:
    # See: https://qqpy.readthedocs.io/zh_CN/latest/ext/commands/commands.html#bool

    if maybe is True:
        return await ctx.send(number * 2)
    await ctx.send(number * 5)


bot.run('token')
