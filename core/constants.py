"""
Constants
"""

class CellEvents:
    START_RUN = 'cell_run_start'
    RESULT = 'cell_result'
    END_RUN = 'cell_run_end'


class CellExecutionStatus:
    DONE = 'done'
    BUSY = 'busy'
    ERROR = 'error'


CELLS_NAMESPACE = '/cells'