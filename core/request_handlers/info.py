# coding: utf8
import json
import tornado.web

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class InfoRequestHandler(tornado.web.RequestHandler):
    """A request handler that returns information on runtime capabilities"""

    def get(self):
        return self.write(
            json.dumps({
                "name": "python-runtime",
                "image": "python",
                "tagRegex": "^(3.*)|latest",
                "modes": ["interactive", "file", "endpoint"],
                "languages": ["shell", "python"]
            }))
