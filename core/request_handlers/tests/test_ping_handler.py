# coding: utf8
import pytest

from support.base_test_handler import TestHandlerBase

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


@pytest.mark.handlers
@pytest.mark.integration
class TestPingHandler(TestHandlerBase):
    def test_ping(self):
        resp = self.fetch('/ping')
        assert resp.code == 200
        assert resp.body == b'pong'
