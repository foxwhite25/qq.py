from typing import Callable


class ConnectionState:
    if TYPE_CHECKING:
        _get_websocket: Callable[..., QQWebSocket]
        _get_client: Callable[..., Client]
        _parsers: Dict[str, Callable[[Dict[str, Any]], None]]

    def __init__(
        self,
        *,
        dispatch: Callable,
        handlers: Dict[str, Callable],
        hooks: Dict[str, Callable],
        http: HTTPClient,
        loop: asyncio.AbstractEventLoop,
        **options: Any,
    ) -> None:
        self.loop: asyncio.AbstractEventLoop = loop
        self.http: HTTPClient = http
        self.max_messages: Optional[int] = options.get('max_messages', 1000)
        if self.max_messages is not None and self.max_messages <= 0:
            self.max_messages = 1000

        self.dispatch: Callable = dispatch
        self.handlers: Dict[str, Callable] = handlers
        self.hooks: Dict[str, Callable] = hooks
        self.shard_count: Optional[int] = None
        self._ready_task: Optional[asyncio.Task] = None
        self.application_id: Optional[int] = utils._get_as_snowflake(options, 'application_id')
        self.heartbeat_timeout: float = options.get('heartbeat_timeout', 60.0)
        self.guild_ready_timeout: float = options.get('guild_ready_timeout', 2.0)
        if self.guild_ready_timeout < 0:
            raise ValueError('guild_ready_timeout cannot be negative')

        allowed_mentions = options.get('allowed_mentions')

        if allowed_mentions is not None and not isinstance(allowed_mentions, AllowedMentions):
            raise TypeError('allowed_mentions parameter must be AllowedMentions')

        self.allowed_mentions: Optional[AllowedMentions] = allowed_mentions
        self._chunk_requests: Dict[Union[int, str], ChunkRequest] = {}

        activity = options.get('activity', None)
        if activity:
            if not isinstance(activity, BaseActivity):
                raise TypeError('activity parameter must derive from BaseActivity.')

            activity = activity.to_dict()

        status = options.get('status', None)
        if status:
            if status is Status.offline:
                status = 'invisible'
            else:
                status = str(status)

        intents = options.get('intents', None)
        if intents is not None:
            if not isinstance(intents, Intents):
                raise TypeError(f'intents parameter must be Intent not {type(intents)!r}')
        else:
            intents = Intents.default()

        if not intents.guilds:
            _log.warning('Guilds intent seems to be disabled. This may cause state related issues.')

        self._chunk_guilds: bool = options.get('chunk_guilds_at_startup', intents.members)

        # Ensure these two are set properly
        if not intents.members and self._chunk_guilds:
            raise ValueError('Intents.members must be enabled to chunk guilds at startup.')

        cache_flags = options.get('member_cache_flags', None)
        if cache_flags is None:
            cache_flags = MemberCacheFlags.from_intents(intents)
        else:
            if not isinstance(cache_flags, MemberCacheFlags):
                raise TypeError(f'member_cache_flags parameter must be MemberCacheFlags not {type(cache_flags)!r}')

            cache_flags._verify_intents(intents)

        self.member_cache_flags: MemberCacheFlags = cache_flags
        self._activity: Optional[ActivityPayload] = activity
        self._status: Optional[str] = status
        self._intents: Intents = intents

        if not intents.members or cache_flags._empty:
            self.store_user = self.create_user  # type: ignore
            self.deref_user = self.deref_user_no_intents  # type: ignore

        self.parsers = parsers = {}
        for attr, func in inspect.getmembers(self):
            if attr.startswith('parse_'):
                parsers[attr[6:].upper()] = func

        self.clear()