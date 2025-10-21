from typing import Self

from bscose.construction.data import Type
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bscose.construction.node import Node # Is this circular? Sure seems like it.


#TODO: Need to properly type dtype, not just use string, see `data.py`
class Port:
    def __init__(self, name: str, dtype: type[Type]):
        self._name = name
        self._type = dtype()

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> Type:
        return self._type

class Sender(Port):
    def __init__(self, name: str, dtype: type[Type]):
        super().__init__(name, dtype)
        self._targets: set[tuple[Node, Receiver]] = set() # list of targets, both Node and Port
        #TODO self._targets may need to be dict[Node, set(Receiver)] to prevent double-

    def has_connections(self) -> bool:
        return len(self._targets) > 0

    def get_num_targets(self) -> int:
        return len(self._targets)

    def get_sorted_targets(self) -> list[tuple["Node", "Receiver"]]:
        return sorted(self._targets, key=lambda r: r[0].name + r[1].name)

    def attach_receiver(self, node: "Node", receiver: "Receiver"):
        if not node.has_specific_receiver(receiver):
            raise ValueError(f"receiver `{receiver.name}` doesn't exist in Node `{node.name}`")
        self._targets.add((node, receiver))

    def detach_receiver(self, node: "Node", receiver: "Receiver", throw_on_missing: bool = False) -> bool:
        if not node.has_specific_receiver(receiver):
            raise ValueError(f"receiver `{receiver.name}` doesn't exist in Node `{node.name}`")

        if (node, receiver) in self._targets:
            self._targets.remove((node, receiver))
            return True
        elif throw_on_missing:
            raise ValueError(f"receiver `{receiver.name}` from Node `{node.name}` not found as a target of Sender `{self.name}`")
        return False

class Receiver(Port):
    def __init__(self, name: str, dtype: type[Type]):
        super().__init__(name, dtype)
        self._source: tuple[Node, Sender] | None = None # list of targets, both Node and Port

    def has_source(self) -> bool:
        return self._source is not None

    def set_source(self, node: "Node", sender: Sender) -> None:
        if self._source is not None:
            raise RuntimeError(f"receiver `{self.name}` has already been attached to `{sender.name}` in "
                             f"Node `{node.name}`, please detach explicitly first")
        self._source = (node, sender)

    def clear_source(self, throw_if_not_attached: bool = True) -> None:
        if self._source is None and throw_if_not_attached:
            raise RuntimeError(f"Nothing to clear: no Sender set for Receiver `{self.name}`")


    @property
    def source(self) -> tuple[Self, Sender] | None:
        return self._source

    def get_source_node(self) -> "Node":
        return self._source[0] if self.has_source() else None

    def get_source_sender(self) -> Sender:
        return self._source[1] if self.has_source() else None
