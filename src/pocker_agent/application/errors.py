class WorkflowError(Exception):
    """A public, expected failure of a workspace command."""

    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.status = status


class OperationCancelled(Exception):
    """Internal control flow; a cancelled operation must never publish output."""
