import os
from .base import BaseConfig
from support.socket import HttpSocketIO


class DevelopmentConfig(BaseConfig):
    """Dev config"""
    SERVER_URI = os.environ['UNKLEARN_SERVER_URI']

    MODES = os.environ['UNKLEARN_RUNTIME_MODES'].split(',')
    LANGUAGES = os.environ['UNKLEARN_RUNTIME_LANGUAGES'].split(',')

    SOCKETIO = HttpSocketIO(SERVER_URI)
    AUTORELOAD = True
