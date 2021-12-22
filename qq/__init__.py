__path__ = __import__('pkgutil').extend_path(__path__, __name__)
__title__ = 'qq'
__author__ = 'Foxwhite'
__license__ = 'MIT'
__version__ = '1.0.7'

import logging
from typing import NamedTuple, Literal
from .client import *
from .user import *
from .channel import *
from .guild import *
from .flags import *
from .member import *
from .message import *
from .asset import *
from .role import *
from .file import *
from .colour import *
from .object import *
from . import utils, abc
from .enum import *
from .shard import *
from .error import *
from .embeds import *
from .mention import *
from .partial_emoji import *
from .raw_models import *


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


version_info: VersionInfo = VersionInfo(major=1, minor=0, micro=7, releaselevel='beta', serial=0)
