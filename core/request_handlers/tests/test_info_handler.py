# coding: utf8
import pytest
import json

from support.base_test_handler import TestHandlerBase

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


@pytest.mark.handlers
@pytest.mark.integration
class TestInfoHandler(TestHandlerBase):
    def test_info(self):
        resp = self.fetch('/info')
        assert resp.code == 200
        assert resp.body.decode('utf-8') == json.dumps({
            "name": "python-runtime",
            "image": "python",
            "tagRegex": "^(3.*)|latest",
            "modes": ["interactive", "file", "endpoint"],
            "languages": ["shell", "python"]
        })
