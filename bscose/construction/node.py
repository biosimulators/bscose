from typing import Self, TypeVar

from bscose.construction.event import (Event,
                                       Announcer
                                       )
from bscose.construction.port import Receiver, Sender
import data
SomeTypeOfNode = TypeVar("SomeTypeOfNode", bound='Node', contravariant=True)


class Node:
    def __init__(self, name: str, *args, **kwargs) -> None:
        if self.__class__ == Node:
            error_msg = f"`{self.__class__.__name__}` is a shared-behavior class that should not be instantiated directly."
            raise NotImplementedError(error_msg)
        if name is None:
            raise TypeError("`name` cannot be None")
        if name == "":
            raise TypeError("`name` cannot be empty")
        self._name = name
        #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
        self._inputs: dict[str, Receiver] = {}
        self._unset_receivers: list[str] = []
        #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
        self._outputs: dict[str, Sender] = {}
        self._unused_outputs: list[str] = []
        #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
        self.parameter_change_announcer: Announcer = Announcer()

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def get_existing_wiring(cls, output_node: Self, input_node: Self):
        wiring_mapping = []
        for port in input_node.get_input_list():
            if not port.has_source() or output_node is not port.get_source_node():
                continue
            wiring_mapping.append((port.get_source_sender(), port))
        return wiring_mapping

    @classmethod
    def generate_autowired_mapping(cls, output_node: Self, input_node: Self, valid_names: set[str] | None = None,
                                   skip_on_bound_receivers: bool = False) -> list[tuple[Sender, Receiver]]:
        # This is auto-generation; we only care about the intersections of names and types
        wiring_mapping = []
        # Determine valid names
        all_shared_names = set.intersection(set(input_node._outputs), set(output_node._outputs))
        all_valid_names = all_shared_names if valid_names is None else set.intersection(all_shared_names, valid_names)
        # iterate through valid names
        for name_to_match_on in list(all_valid_names):
            sender: Sender = output_node._outputs[name_to_match_on]
            receiver: Receiver = input_node._inputs[name_to_match_on]

            if receiver.has_source():
                if skip_on_bound_receivers:
                    continue
                bound_node: Self = receiver.get_source_node()
                bound_sender: Sender = receiver.get_source_sender()
                raise ValueError(f"Receiver `{receiver}`({name_to_match_on}) on Node `{input_node}`({input_node._name}) "
                                 f"is already bound to `{bound_sender}`({bound_sender.name}) on Node `{bound_node}`({bound_node._name}) ")
            wiring_mapping.append((sender, receiver))
        return wiring_mapping

    @classmethod
    def connect_to_dependency(cls, output_node: Self, input_node: Self,
                              storage_names_to_wire: list[tuple[Sender, Receiver]] | list[str] | None = None) -> None:
        if storage_names_to_wire is None:
            auto_wiring = Node.generate_autowired_mapping(output_node, input_node, skip_on_bound_receivers=True)
            Node.__connect_to_dependency(output_node, input_node, auto_wiring)
            return

        if not isinstance(storage_names_to_wire, list):
            raise ValueError(f"`storage_names_to_wire` has unknown type `{type(storage_names_to_wire)}`.")

        example_element = storage_names_to_wire[0]
        if (isinstance(example_element, tuple) and
                len(example_element) == 2 and
                isinstance(example_element[0], Sender) and
                isinstance(example_element[1], Receiver)):
            storage_names_to_wire: list[tuple[Sender, Receiver]]
            Node.__connect_to_dependency(output_node, input_node, storage_names_to_wire)
        elif isinstance(example_element, str):
            storage_names_to_wire: list[str]
            valid_names_set: set[str] = set(storage_names_to_wire)
            auto_wiring = Node.generate_autowired_mapping(output_node, input_node, valid_names_set, False) # we *do* throw on bound nodes, because the *user* provided the wires!
            Node.__connect_to_dependency(output_node, input_node, auto_wiring)


    #TODO: Upgrade to allow custom name matching and type matching
    @classmethod
    def __connect_to_dependency(cls, output_node: Self, input_node: Self, storage_wiring: list[tuple[Sender, Receiver]]) -> None:
        if input_node == output_node:
            raise ValueError("Bad loop detected: You can not connect outputs to the inputs of the same Node!")
        if storage_wiring is None:
            raise ValueError("`storage_wiring` cannot be None.")

        for sender, receiver in storage_wiring:
            # perform type confirmations
            if sender.type != receiver.type:
                output_str = f"output:`{sender.name}: {sender.type}`({output_node._name})"
                input_str = f"input:`{receiver.type}: {receiver.type}`({input_node._name})"
                err_msg = f"Desired wiring has type mis-match: {output_str} vs {input_str}."
                raise ValueError(err_msg)

            # There are 4 types of connections that could be theoretically made:
            # Single Output -> Single Input (SOSI) => We allow this.
            # Multi Output -> Single Input (MOSI) => We CAN'T allow this (at the moment at least).
            # Single Output -> Multi Input (SOMI) => We allow this.
            # Multi Output -> Multi Input (MOMI) => Depending on how you define this, we may or may not be able
            #    to do this. The key is no MOSI relationship can be formed through MOMI for it to be valid!

            # also note: this function does *NOT* assume which of the two nodes are inputs / outputs!
            # That has to be determined for *each* wire.
            # connection variables
            # if we're connecting to an "input variable" (hopefully not)
            if receiver.has_source():
                raise ValueError(f"input store `{receiver.name}` is already connected "
                                 + f"to node `{receiver.get_source_node()._name}`. "
                                 + "Inputs cannot have multiple connections.")
            # Perform the connection, sender-side first
            sender.attach_receiver(input_node, receiver)
            receiver.set_source(output_node, sender)
            #input_node.parameter_change_announcer.announce_event(ParametersChangedEvent(input_node))


    def has_specific_receiver(self, receiver: Receiver) -> bool:
        if receiver.name in self._inputs and receiver == self._inputs[receiver.name]:
            return True
        return False

    def has_specific_sender(self, sender: Sender) -> bool:
        if sender.name in self._outputs and sender == self._outputs[sender.name]:
            return True
        return False

    def get_inputs(self) -> list[tuple[str, type[data.Type]]]:
        return [ (receiver.name, type(receiver.type)) for receiver in self._inputs.values() ]

    def get_outputs(self) -> list[tuple[str, type[data.Type]]]:
        return [ (sender.name, type(sender.type)) for sender in self._outputs.values() ]

    def get_input_list(self) -> list[Receiver]:
        return list(self._inputs.values())

    def get_output_list(self) -> list[Sender]:
        return list(self._outputs.values())

    def get_parameters(self) -> set[Receiver]:
        return {input_port for input_port in self._inputs.values() if not input_port.has_source()}

    def get_unused_outputs(self) -> set[Sender]:
        return {output_port for output_port in self._outputs.values() if not output_port.has_connections()}

    def has_inputs_with_sources(self) -> bool:
        return len(self._unset_receivers) < len(self._inputs)

    def has_outputs_with_targets(self) -> bool:
        return len(self._unused_outputs) < len(self._outputs)

    def __add_receiver(self, receiver: Receiver) -> None:
        if receiver.name in self._inputs:
            if receiver == self._inputs[receiver.name]:
                return # getting here means adding is redundant
            raise ValueError(f"Receiver `{receiver.name}` is already an existing Receiver. ")
        self._inputs[receiver.name] = receiver
        self._unset_receivers.append(receiver.name)

    def __add_sender(self, receiver: Receiver) -> None:
        if receiver.name in self._inputs:
            if receiver == self._inputs[receiver.name]:
                return # getting here means adding is redundant
            raise ValueError(f"Receiver `{receiver.name}` is already an existing Receiver. ")
        self._inputs[receiver.name] = receiver
        self._unset_receivers.append(receiver.name)

#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
#               Node Definitions                #
#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #

class Repetition(Node): # task repetitively done, each tick of the clock
    def __init__(self, name: str, *args, **kwargs) -> None:
        super().__init__(name, *args, **kwargs)
        raise NotImplementedError()

class Operation(Node): # task runs based on dependency changes
    def __init__(self, name: str, *args, **kwargs) -> None:
        if self.__class__ == Operation:
            error_msg = f"`{self.__class__.__name__}` is a shared-behavior class that should not be instantiated directly."
            raise NotImplementedError(error_msg)
        super().__init__(name, *args, **kwargs)

class PatientOperation(Operation): # task runs a single time once all dependencies finish
    def __init__(self, name: str, *args, **kwargs) -> None:
        super().__init__(name, *args, **kwargs)

class EagerOperation(Operation): # task runs anytime
    def __init__(self, name: str, *args, **kwargs) -> None:
        super().__init__(name, *args, **kwargs)


#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
#               Event Definitions               #
#  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #

class ParametersChangedEvent(Event):
    def __init__(self, node: Node) -> None:
        super().__init__(f"Parameters in node `{node.name}` changed.")
        self.node = node
