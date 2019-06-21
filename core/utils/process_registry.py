# coding: utf8

__author__ = 'Tharun Mathew Paul (tmpaul06@gmail.com)'


class ProcessRegistryObject:
    """An object that is stored inside a process registry"""

    def __init__(self, registry, cell_id):
        self._registry = registry
        self.cell_id = cell_id
        self._process = None

    def register(self, process):
        self._process = process
        self._registry.add(self)

    def deregister(self):
        self._registry.remove(self)

    def get_process(self):
        return self._process


class ProcessRegistry:
    """A class that maps a notebook cell run to a process"""

    def __init__(self):
        self.registry = {}

    def add(self, pro):
        """Add a new process registry object to registry"""
        self.registry[pro.cell_id] = pro

    def remove(self, pro):
        self.registry.pop(pro.cell_id, None)

    def get_process_info(self, cell_id):
        return self.registry.get(cell_id, None)
