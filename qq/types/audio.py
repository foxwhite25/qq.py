from typing import TypedDict, Literal

Status = Literal[0, 1, 2, 3]


class AudioAction(TypedDict):
    guild_id: str
    channel_id: str
    audio_url: str
    text: str


class _BaseAudioControl(TypedDict):
    audio_url: str
    text: str


class StartAudioControl(_BaseAudioControl):
    status: Literal[0]


class PauseAudioControl(_BaseAudioControl):
    status: Literal[1]


class ResumeAudioControl(_BaseAudioControl):
    status: Literal[2]


class StopAudioControl(_BaseAudioControl):
    status: Literal[3]
