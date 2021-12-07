from __future__ import annotations

import datetime
import io
import re
from os import PathLike
from typing import Union, Optional, TYPE_CHECKING, ClassVar, Tuple, List, Callable, overload, Any

from .abc import MessageableChannel, PartialMessageableChannel
from .channel import TextChannel
from .embeds import Embed
from .enum import ChannelType
from .guild import Guild, GuildChannel
from . import utils
from .file import File
from .member import Member
from .mixins import Hashable
from .role import Role
from .state import ConnectionState
from .types.message import Attachment as AttachmentPayload, Message as MessagePayload
from .types.embed import Embed as EmbedPayload
from .types.user import User as UserPayload
from .types.member import Member as MemberPayload, UserWithMember as UserWithMemberPayload
from .user import User
from .utils import escape_mentions


class Attachment(Hashable):
    __slots__ = ('id', 'size', 'height', 'width', 'filename', 'url', 'proxy_url', '_http', 'content_type')

    def __init__(self, *, data: AttachmentPayload, state: ConnectionState):
        self.url: str = data.get('url')
        self._http = state.http

    def is_spoiler(self) -> bool:
        """:class:`bool`: Whether this attachment contains a spoiler."""
        return self.filename.startswith('SPOILER_')

    def __repr__(self) -> str:
        return f'<Attachment id={self.id} filename={self.filename!r} url={self.url!r}>'

    def __str__(self) -> str:
        return self.url or ''

    async def save(
            self,
            fp: Union[io.BufferedIOBase, PathLike],
            *,
            seek_begin: bool = True,
            use_cached: bool = False,
    ) -> int:
        data = await self.read(use_cached=use_cached)
        if isinstance(fp, io.BufferedIOBase):
            written = fp.write(data)
            if seek_begin:
                fp.seek(0)
            return written
        else:
            with open(fp, 'wb') as f:
                return f.write(data)

    async def read(self, *, use_cached: bool = False) -> bytes:
        url = self.proxy_url if use_cached else self.url
        data = await self._http.get_from_cdn(url)
        return data

    async def to_file(self, *, use_cached: bool = False, spoiler: bool = False) -> File:
        data = await self.read(use_cached=use_cached)
        return File(io.BytesIO(data), filename=self.filename, spoiler=spoiler)

    def to_dict(self) -> AttachmentPayload:
        result: AttachmentPayload = {'url': self.url}
        return result


def flatten_handlers(cls):
    prefix = len('_handle_')
    handlers = [
        (key[prefix:], value)
        for key, value in cls.__dict__.items()
        if key.startswith('_handle_') and key != '_handle_member'
    ]

    # store _handle_member last
    handlers.append(('member', cls._handle_member))
    cls._HANDLERS = handlers
    cls._CACHED_SLOTS = [attr for attr in cls.__slots__ if attr.startswith('_cs_')]
    return cls


@flatten_handlers
class Message(Hashable):
    __slots__ = (
        '_state',
        '_edited_timestamp',
        '_cs_channel_mentions',
        '_cs_raw_mentions',
        '_cs_clean_content',
        '_cs_raw_channel_mentions',
        '_cs_system_content',
        'content',
        'channel',
        'mention_everyone',
        'embeds',
        'id',
        'mentions',
        'author',
        'attachments',
        'guild',
    )

    if TYPE_CHECKING:
        _HANDLERS: ClassVar[List[Tuple[str, Callable[..., None]]]]
        _CACHED_SLOTS: ClassVar[List[str]]
        guild: Optional[Guild]
        mentions: List[Union[User, Member]]
        author: Union[User, Member]
        role_mentions: List[Role]

    def __init__(
            self,
            *,
            state: ConnectionState,
            channel: MessageableChannel,
            data: MessagePayload,
    ):
        self._state: ConnectionState = state
        self.id: str = data['id']
        self.attachments: List[Attachment] = [Attachment(data=a, state=self._state) for a in data['attachments']]
        self.embeds: List[Embed] = [Embed.from_dict(a) for a in data['embeds']]
        self.channel: MessageableChannel = channel
        self._edited_timestamp: Optional[datetime.datetime] = utils.parse_time(data['edited_timestamp'])
        self.mention_everyone: bool = data['mention_everyone']
        self.content: str = data['content']

        try:
            # if the channel doesn't have a guild attribute, we handle that
            self.guild = channel.guild  # type: ignore
        except AttributeError:
            self.guild = state._get_guild(data.get('guild_id'))

        for handler in ('author', 'member', 'mentions'):
            try:
                getattr(self, f'_handle_{handler}')(data[handler])
            except KeyError:
                continue

    def __repr__(self) -> str:
        name = self.__class__.__name__
        return (
            f'<{name} id={self.id} channel={self.channel!r} type={self.type!r} author={self.author!r}>'
        )

    def _try_patch(self, data, key, transform=None) -> None:
        try:
            value = data[key]
        except KeyError:
            pass
        else:
            if transform is None:
                setattr(self, key, value)
            else:
                setattr(self, key, transform(value))

    def _update(self, data):
        # In an update scheme, 'author' key has to be handled before 'member'
        # otherwise they overwrite each other which is undesirable.
        # Since there's no good way to do this we have to iterate over every
        # handler rather than iterating over the keys which is a little slower
        for key, handler in self._HANDLERS:
            try:
                value = data[key]
            except KeyError:
                continue
            else:
                handler(self, value)

        # clear the cached properties
        for attr in self._CACHED_SLOTS:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    def _handle_edited_timestamp(self, value: str) -> None:
        self._edited_timestamp = utils.parse_time(value)

    def _handle_mention_everyone(self, value: bool) -> None:
        self.mention_everyone = value

    def _handle_content(self, value: str) -> None:
        self.content = value

    def _handle_attachments(self, value: List[AttachmentPayload]) -> None:
        self.attachments = [Attachment(data=a, state=self._state) for a in value]

    def _handle_embeds(self, value: List[EmbedPayload]) -> None:
        self.embeds = [Embed.from_dict(data) for data in value]

    def _handle_author(self, author: UserPayload) -> None:
        self.author = self._state.store_user(author)
        if isinstance(self.guild, Guild):
            found = self.guild.get_member(self.author.id)
            if found is not None:
                self.author = found

    def _handle_member(self, member: MemberPayload) -> None:
        author = self.author
        try:
            # Update member reference
            author._update_from_message(member)  # type: ignore
        except AttributeError:
            # It's a user here
            self.author = Member._from_message(message=self, data=member)

    def _handle_mentions(self, mentions: List[UserWithMemberPayload]) -> None:
        self.mentions = r = []
        guild = self.guild
        state = self._state
        if not isinstance(guild, Guild):
            self.mentions = [state.store_user(m) for m in mentions]
            return

        for mention in filter(None, mentions):
            id_search = int(mention['id'])
            member = guild.get_member(id_search)
            if member is not None:
                r.append(member)
            else:
                r.append(Member._try_upgrade(data=mention, guild=guild, state=state))

    def _rebind_cached_references(self, new_guild: Guild, new_channel: TextChannel) -> None:
        self.guild = new_guild
        self.channel = new_channel

    @utils.cached_slot_property('_cs_raw_mentions')
    def raw_mentions(self) -> List[int]:
        """List[:class:`int`]: A property that returns an array of user IDs matched with
        the syntax of ``<@user_id>`` in the message content.
        This allows you to receive the user IDs of mentioned users
        even in a private message context.
        """
        return [int(x) for x in re.findall(r'<@!?([0-9]{15,20})>', self.content)]

    @utils.cached_slot_property('_cs_raw_channel_mentions')
    def raw_channel_mentions(self) -> List[int]:
        """List[:class:`int`]: A property that returns an array of channel IDs matched with
        the syntax of ``<#channel_id>`` in the message content.
        """
        return [int(x) for x in re.findall(r'<#([0-9]{15,20})>', self.content)]

    @utils.cached_slot_property('_cs_channel_mentions')
    def channel_mentions(self) -> List[GuildChannel]:
        if self.guild is None:
            return []
        it = filter(None, map(self.guild.get_channel, self.raw_channel_mentions))
        return utils._unique(it)

    @utils.cached_slot_property('_cs_clean_content')
    def clean_content(self) -> str:
        # fmt: off
        transformations = {
            re.escape(f'<#{channel.id}>'): '#' + channel.name
            for channel in self.channel_mentions
        }

        mention_transforms = {
            re.escape(f'<@{member.id}>'): '@' + member.display_name
            for member in self.mentions
        }

        # add the <@!user_id> cases as well..
        second_mention_transforms = {
            re.escape(f'<@{member.id}>'): '@' + member.display_name
            for member in self.mentions
        }

        transformations.update(mention_transforms)
        transformations.update(second_mention_transforms)

        if self.guild is not None:
            role_transforms = {
                re.escape(f'<@&{role.id}>'): '@' + role.name
                for role in self.role_mentions
            }
            transformations.update(role_transforms)

        # fmt: on

        def repl(obj):
            return transformations.get(re.escape(obj.group(0)), '')

        pattern = re.compile('|'.join(transformations.keys()))
        result = pattern.sub(repl, self.content)
        return escape_mentions(result)

    @property
    def edited_at(self) -> Optional[datetime.datetime]:
        return self._edited_timestamp

    async def reply(self, content: Optional[str] = None, **kwargs) -> Message:
        return await self.channel.send(content, reference=self, **kwargs)


class PartialMessage(Hashable):
    __slots__ = ('channel', 'id', '_cs_guild', '_state')

    jump_url: str = Message.jump_url  # type: ignore
    delete = Message.delete
    publish = Message.publish
    pin = Message.pin
    unpin = Message.unpin
    add_reaction = Message.add_reaction
    remove_reaction = Message.remove_reaction
    clear_reaction = Message.clear_reaction
    clear_reactions = Message.clear_reactions
    reply = Message.reply
    to_reference = Message.to_reference
    to_message_reference_dict = Message.to_message_reference_dict

    def __init__(self, *, channel: PartialMessageableChannel, id: int):
        if channel.type not in (
                ChannelType.text,
        ):
            raise TypeError(f'Expected TextChannel,not {type(channel)!r}')

        self.channel: PartialMessageableChannel = channel
        self._state: ConnectionState = channel._state
        self.id: int = id

    def _update(self, data) -> None:
        # This is used for duck typing purposes.
        # Just do nothing with the data.
        pass

    # Also needed for duck typing purposes
    # n.b. not exposed

    def __repr__(self) -> str:
        return f'<PartialMessage id={self.id} channel={self.channel!r}>'

    @utils.cached_slot_property('_cs_guild')
    def guild(self) -> Optional[Guild]:
        """Optional[:class:`Guild`]: The guild that the partial message belongs to, if applicable."""
        return getattr(self.channel, 'guild', None)

    async def fetch(self) -> Message:
        data = await self._state.http.get_message(self.channel.id, self.id)
        return self._state.create_message(channel=self.channel, data=data)
