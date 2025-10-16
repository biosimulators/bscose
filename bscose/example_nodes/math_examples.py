from bscose.construction.node import Node, Operation, PatientOperation, Repetition
from bscose.construction.port import Sender, Receiver
from bscose.construction.data import Type, Unit, Classification

class RealNumber(Type):
    def __init__(self) -> None:
        super().__init__()

class Float(RealNumber):
    def __init__(self) -> None:
        super().__init__()

class Integer(RealNumber):
    def __init__(self) -> None:
        super().__init__()

class Increment(PatientOperation):
    def __init__(self, name: str, *args, **kwargs) -> None:
        super().__init__(name, *args, **kwargs)
        self._add_receiver(Receiver("value", RealNumber))
        self._add_sender(Sender("result", RealNumber))

class Addition(PatientOperation):
    def __init__(self, name: str, *args, **kwargs) -> None:
        super().__init__(name, *args, **kwargs)
        self._add_receiver(Receiver("addend_1", RealNumber))
        self._add_receiver(Receiver("addend_2", RealNumber))
        self._add_sender(Sender("result", RealNumber))