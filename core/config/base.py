import os


class BaseConfig:
    """A class that represents base configuration"""
    SERVER_URI = None
    REDIS_BROKER_URL = None

    MODES = ['interactive', 'file', 'endpoint', 'daemon']

    LANGUAGES = ['shell', 'python']

    FILE_ROOT_DIR = '/tmp/code-files'

    ENDPOINT_CONFIG_ROOT_DIR = '/tmp/endpoint-configs'

    SOCKETIO = None
