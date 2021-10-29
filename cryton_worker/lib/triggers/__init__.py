from enum import Enum, EnumMeta

from cryton_worker.lib.util import exceptions
from cryton_worker.lib.triggers.trigger_base import Trigger
from cryton_worker.lib.triggers.trigger_http import HTTPTrigger
from cryton_worker.lib.triggers.trigger_msf import MSFTrigger


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
    MSF = MSFTrigger
