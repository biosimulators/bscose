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
        input_num_name = "input_num"
        output_num_name = "output_num"

        self._inputs[input_num_name] = Receiver(input_num_name, RealNumber)
        self._outputs[output_num_name] = Sender(output_num_name, RealNumber)