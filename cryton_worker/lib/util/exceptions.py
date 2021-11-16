class Error(Exception):
    """Base class for exceptions in this module."""


class TriggerError(Error):
    """Base class for Trigger exceptions."""


class MsfSessionError(Error):
    """Base class for Session exceptions."""


class MsfSessionNotFound(MsfSessionError):
    """Exception raised when Session ID was not found in msf."""
    def __init__(self, session_id: str):
        self.message = f"Session '{session_id}' not found in msf."
        super().__init__(self.message)


class MsfSessionError(Error):
    """Base class for Session exceptions."""


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
