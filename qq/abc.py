from typing import overload, Optional, Union, List

from .error import InvalidArgument
from .mention import AllowedMentions
from .state import ConnectionState


class Messageable:
    """An ABC that details the common operations on a model that can send messages.
    The following implement this ABC:
    - :class:`~discord.TextChannel`
    - :class:`~discord.DMChannel`
    - :class:`~discord.GroupChannel`
    - :class:`~discord.User`
    - :class:`~discord.Member`
    - :class:`~discord.ext.commands.Context`
    - :class:`~discord.Thread`
    """

    __slots__ = ()
    _state: ConnectionState

    async def _get_channel(self) -> MessageableChannel:
        raise NotImplementedError

    @overload
    async def send(
        self,
        content: Optional[str] = ...,
        *,
        tts: bool = ...,
        nonce: Union[str, int] = ...,
        allowed_mentions: AllowedMentions = ...,
        reference: Union[Message, MessageReference, PartialMessage] = ...,
        mention_author: bool = ...,
    ) -> Message:
        ...

    async def send(
        self,
        content=None,
        *,
        tts=None,
        nonce=None,
        allowed_mentions=None,
        reference=None,
        mention_author=None,
    ):

        channel = await self._get_channel()
        state = self._state
        content = str(content) if content is not None else None

        if allowed_mentions is not None:
            if state.allowed_mentions is not None:
                allowed_mentions = state.allowed_mentions.merge(allowed_mentions).to_dict()
            else:
                allowed_mentions = allowed_mentions.to_dict()
        else:
            allowed_mentions = state.allowed_mentions and state.allowed_mentions.to_dict()

        if mention_author is not None:
            allowed_mentions = allowed_mentions or AllowedMentions().to_dict()
            allowed_mentions['replied_user'] = bool(mention_author)

        if reference is not None:
            try:
                reference = reference.to_message_reference_dict()
            except AttributeError:
                raise InvalidArgument('reference parameter must be Message, MessageReference, or PartialMessage') from None

        data = await state.http.send_message(
            channel.id,
            content,
            tts=tts,
            nonce=nonce,
            allowed_mentions=allowed_mentions,
            message_reference=reference,
        )

        ret = state.create_message(channel=channel, data=data)
        return ret

    async def fetch_message(self, id: int, /) -> Message:
        """|coro|
        Retrieves a single :class:`~discord.Message` from the destination.
        Parameters
        ------------
        id: :class:`int`
            The message ID to look for.
        Raises
        --------
        ~discord.NotFound
            The specified message was not found.
        ~discord.Forbidden
            You do not have the permissions required to get a message.
        ~discord.HTTPException
            Retrieving the message failed.
        Returns
        --------
        :class:`~discord.Message`
            The message asked for.
        """
        id = str(id)
        channel = await self._get_channel()
        data = await self._state.http.get_message(channel.id, id)
        return self._state.create_message(channel=channel, data=data)