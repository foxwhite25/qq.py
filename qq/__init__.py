__title__ = 'qq'
__author__ = 'Foxwhite'
__license__ = 'MIT'
__version__ = '0.0.5'

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

import logging

from .client import *
from .guild import *


logging.getLogger(__name__).addHandler(logging.NullHandler())
