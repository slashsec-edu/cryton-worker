class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class TriggerTypeDoesNotExist(Error):
    """Exception raised when Trigger type doesn't match existing types."""
    def __init__(self, trigger_type: str, existing_triggers: list):
        self.message = f"Nonexistent trigger type '{trigger_type}'. " \
                       f"Supported trigger types are: {', '.join(existing_triggers)}."
        super().__init__(self.message)
