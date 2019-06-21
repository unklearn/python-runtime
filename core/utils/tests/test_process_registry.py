# coding: utf8
import pytest

from ..process_registry import ProcessRegistry, ProcessRegistryObject

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class FakePRO:
    def __init__(self):
        self.cell_id = 'cid'


@pytest.mark.unit
@pytest.mark.utils
def test_process_registry_add():
    r = ProcessRegistry()

    pro = FakePRO()
    r.add(pro)

    assert r.get_process_info('cid') is pro


@pytest.mark.unit
@pytest.mark.utils
def test_process_registry_remove():
    r = ProcessRegistry()

    pro = FakePRO()
    r.add(pro)

    assert r.get_process_info('cid') is pro

    r.remove(pro)

    assert r.get_process_info('cid') is None


@pytest.mark.unit
@pytest.mark.utils
def test_process_registry_object_register():
    r = ProcessRegistry()

    pro = ProcessRegistryObject(r, 'cid')

    pro.register('p')

    assert pro.get_process() is 'p'

    assert r.get_process_info('cid') is pro


@pytest.mark.unit
@pytest.mark.utils
def test_process_registry_object_deregister():
    r = ProcessRegistry()

    pro = ProcessRegistryObject(r, 'cid')

    pro.register('p')

    pro.deregister()

    assert r.get_process_info('cid') is None
