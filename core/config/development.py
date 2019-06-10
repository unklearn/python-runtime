import os
from .base import BaseConfig
from flask_socketio import SocketIO


class DevelopmentConfig(BaseConfig):
    """Dev config"""
    SERVER_URI = os.environ['UNKLEARN_SERVER_URI']
    REDIS_BROKER_URL = os.environ['UNKLEARN_REDIS_BROKER_URL']

    MODES = os.environ['UNKLEARN_RUNTIME_MODES'].split(',')
    LANGUAGES = os.environ['UNKLEARN_RUNTIME_LANGUAGES'].split(',')

    SOCKETIO = SocketIO(message_queue=REDIS_BROKER_URL)