__title__ = 'qq'
__author__ = 'Foxwhite'
__license__ = 'MIT'
__version__ = '0.1.3'

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

import logging
from typing import NamedTuple
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


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


version_info: VersionInfo = VersionInfo(major=0, minor=1, micro=3, releaselevel='alpha', serial=0)
