#  The MIT License (MIT)
#  Copyright (c) 2021-present foxwhite25
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.

from __future__ import annotations

from typing import TYPE_CHECKING

from . import abc
from .enum import AudioStatusType, try_enum

if TYPE_CHECKING:
    from .types.audio import (
        StartAudioControl as StartAudioControlPayload,
        PauseAudioControl as PauseAudioControlPayload,
        ResumeAudioControl as ResumeAudioControlPayload,
        StopAudioControl as StopAudioControlPayload,
        AudioAction as AudioActionPayload
    )


class AudioAction:
    """代表音频频道中的状态

    .. container:: operations
        .. describe:: str(x)

            返回状态文本。

    Attributes
    -----------
    audio_url: Optional[:class:`str`]
        音频数据的url，可能为 ``None`` 。
    text: Optional[:class:`Guild`]
        状态文本，可能为 ``None`` 。
    guild_id: :class:`int`
        音频的频道 ID。
    channel_id: Optional[:class:`int`]
        音频的子频道 ID。
    """

    __slots__ = (
        'audio_url',
        'text',
        'guild_id',
        'channel_id'
    )

    def __init__(self, data: AudioActionPayload):
        self.audio_url = data.get('audio_url')
        self.text = data.get('text')
        self.guild_id = data.get('guild_id')
        self.channel_id = data.get('channel_id')


class StartAudio(abc.BaseAudioControl):
    """代表音频频道中的开始播放动作

    .. container:: operations
        .. describe:: str(x)

            返回状态文本。

    """

    __slots__ = (
        '_audio_url',
        '_text',
        '_status'
    )

    def __init__(self, data: StartAudioControlPayload):
        self._status = data.get('status', '')
        self._text = data.get("text", '')
        self._audio_url = data.get("audio_url", '')

    @property
    def type(self) -> AudioStatusType:
        """返回动作的种类
        """
        return try_enum(AudioStatusType, self._status)

    def to_dict(self):
        return {"audio_url": self._audio_url, "text": self._text, "status": self.type}


class PauseAudio(abc.BaseAudioControl):
    """代表音频频道中的暂停播放动作

    .. container:: operations
        .. describe:: str(x)

            返回状态文本。

    """

    __slots__ = (
        '_audio_url',
        '_text',
        '_status'
    )

    def __init__(self, data: PauseAudioControlPayload):
        self._status = data.get('status', '')
        self._text = data.get("text", '')
        self._audio_url = data.get("audio_url", '')

    @property
    def type(self) -> AudioStatusType:
        """返回动作的种类
        """
        return try_enum(AudioStatusType, self._status)

    def to_dict(self):
        return {"status": self.type}


class ResumeAudio(abc.BaseAudioControl):
    """代表音频频道中的继续播放动作

    .. container:: operations
        .. describe:: str(x)

            返回状态文本。

    """

    __slots__ = (
        '_audio_url',
        '_text',
        '_status'
    )

    def __init__(self, data: ResumeAudioControlPayload):
        self._status = data.get('status', '')
        self._text = data.get("text", '')
        self._audio_url = data.get("audio_url", '')

    @property
    def type(self) -> AudioStatusType:
        """返回动作的种类
        """
        return try_enum(AudioStatusType, self._status)

    def to_dict(self):
        return {"status": self.type}


class StopAudio(abc.BaseAudioControl):
    """代表音频频道中的停止播放动作

    .. container:: operations
        .. describe:: str(x)

            返回状态文本。

    """

    __slots__ = (
        '_audio_url',
        '_text',
        '_status'
    )

    def __init__(self, data: StopAudioControlPayload):
        self._status = data.get('status', '')
        self._text = data.get("text", '')
        self._audio_url = data.get("audio_url", '')

    @property
    def type(self) -> AudioStatusType:
        """返回动作的种类
        """
        return try_enum(AudioStatusType, self._status)

    def to_dict(self):
        return {"status": self.type}
