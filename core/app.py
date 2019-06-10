import tornado.web
import os

from core.request_handlers import InteractiveExecutionRequestHandler
from core.request_handlers import FilesHandler, FileExecutionHandler
from core.config import get_current_config

config = get_current_config(os.environ.get('UNKLEARN_ENVIRONMENT_TYPE'))

app = tornado.web.Application([
    (r"/interactive/?", InteractiveExecutionRequestHandler, dict(socketio=config.SOCKETIO)),
    (r"/files/?(?P<file_path>[A-Z0-9a-z_\-.%]+)?", FilesHandler, dict(file_path_root=config.FILE_ROOT_DIR)),
    (r"/file-runs/?", FileExecutionHandler, dict(file_path_root=config.FILE_ROOT_DIR))
])

# Set config on app object
app.config = config