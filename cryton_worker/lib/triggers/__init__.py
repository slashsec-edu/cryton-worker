from enum import Enum, EnumMeta

from cryton_worker.lib.util import exceptions
from cryton_worker.lib.triggers.base_trigger import Trigger
from cryton_worker.lib.triggers.http_trigger import HTTPTrigger


class TriggerTypeMeta(EnumMeta):
    """
    Overrides base metaclass of Enum in order to support custom exception when accessing not present item.
    """
    def __getitem__(self, item):
        try:
            return super().__getitem__(item).value
        except KeyError:
            raise exceptions.TriggerTypeDoesNotExist(item, [trigger.name for trigger in list(self)])


class TriggerEnum(Enum, metaclass=TriggerTypeMeta):
    """
    Keys according to lib.util.constants
    """
    HTTP = HTTPTrigger
