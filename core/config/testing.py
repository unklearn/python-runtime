from support.socket import DummySocketIO
from .base import BaseConfig


class TestingConfig(BaseConfig):
    """Config for testing"""
    SERVER_URI = 'http://localhost:8763'
    REDIS_BROKER_URL = 'redis://redis:6379'

    SOCKETIO = DummySocketIO()

    FILE_ROOT_DIR = '/tmp'
