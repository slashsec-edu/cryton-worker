class Error(Exception):
    """Base class for exceptions in this module."""


class TriggerError(Error):
    """Base class for Trigger exceptions."""


class TriggerTypeDoesNotExist(TriggerError):
    """Exception raised when Trigger type doesn't match existing types."""
    def __init__(self, trigger_type: str, existing_triggers: list):
        self.message = f"Nonexistent trigger type '{trigger_type}'. " \
                       f"Supported trigger types are: {', '.join(existing_triggers)}."
        super().__init__(self.message)


class TooManyActivators(TriggerError):
    """Exception raised when Trigger can't contain more activators."""
    def __init__(self, trigger_type: str):
        self.message = f"Trigger '{trigger_type}' can't contain more activators."
        super().__init__(self.message)
