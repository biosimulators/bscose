from bscose.construction.node import Node, Operation, PatientOperation, Repetition
from bscose.construction.port import Sender, Receiver
from typing import Self, TypeVar, Generic
SomeTypeOfNode = TypeVar("SomeTypeOfNode", bound=Node, contravariant=True)

#TODO: see if we need / can add *args to internal method

class Chain(Generic[SomeTypeOfNode]):
    def __init__(self, starting_node: Node, chain_name: str | None = None) -> None:
        if self.__class__ == Chain:
            error_msg = f"`{self.__class__.__name__}` is a shared-behavior class that should not be instantiated directly."
            raise NotImplementedError(error_msg)
        self._name: str = chain_name if chain_name is not None else self.__class__.__name__
        self._element_list = [starting_node]
        self._element_to_index_mapping = {starting_node: 0}
        self._node_name_map: dict[str, SomeTypeOfNode] = { starting_node.name: starting_node }

    @property
    def name(self) -> str:
        return self._name

    def get(self, name: str) -> Node:
        if name not in self._node_name_map:
            raise ValueError(f"Node with name `{name}` does not exist")
        return self._node_name_map[name]

    def get_all_names(self) -> list[str]:
        return list(self._node_name_map.keys())

    def is_head_node(self, name: str) -> bool:
        return self.get(name) is self._element_list[0]

    def is_head_node_with_no_sources(self, name: str) -> bool:
        if self.get(name) is not self._element_list[0]:
            return False
        return not self._element_list[0].has_inputs_with_sources()

    def get_head_node_name(self) -> str:
        return self._element_list[0].name

    def is_tail_node(self, name: str) -> bool:
        return self.get(name) is self._element_list[-1]

    def is_tail_node_with_no_targets(self, name: str) -> bool:
        if self.get(name) is not self._element_list[-1]:
            return False
        return not self._element_list[-1].has_inputs_with_sources()

    def get_tail_node_name(self) -> str:
        return self._element_list[-1].name

    def size(self):
        return len(self._element_list)

    def append(self, name: str, node_type: type[Operation], *node_construction_args, **node_construction_kwargs) -> Self:
        if name in self._node_name_map:
            raise KeyError(f"Node `{name}` already exists in chain {self.__class__.__name__}")
        attachment_node = self._element_list[-1]
        new_node = node_type(name, *node_construction_args, **node_construction_kwargs)
        try:
            Node.connect_to_dependency(attachment_node, new_node)
        except ValueError as e:
            raise ValueError(f"Unable to extend chain with node `{name}`", e)
        self._element_list.append(new_node)
        self._element_to_index_mapping[new_node] = len(self._element_list)
        self._node_name_map[name] = new_node

    def remove_with_everything_following(self, name: str, throw_if_not_found: bool = True) -> Self:
        if name not in self._node_name_map:
            if throw_if_not_found:
                raise ValueError(f"Node `{name}` not found in chain `{self.__class__.__name__}`")
            return Self # else, nothing to do
        try:
            self.split(name)
        except ValueError as e:
            if throw_if_not_found:
                raise e
        except IndexError | TypeError as e:
            raise e # we still want to declare error in these cases

        del self._element_to_index_mapping[self._node_name_map[name]]
        del self._node_name_map[name]
        self._element_list.pop()
        return self

    """
    Splits at index, such that all *following* nodes become their own chain
    """
    def split(self, node_name_or_index: str | int) -> Self:
        if not isinstance(node_name_or_index, int) and not isinstance(node_name_or_index, str):
            raise TypeError("`node_or_index` must be an instance of `Node` or and integer index")

        if isinstance(node_name_or_index, str) and (node_name_or_index not in self._node_name_map
                                                    or self._node_name_map[node_name_or_index] not in self._element_to_index_mapping):
            raise ValueError(f"Node `{node_name_or_index}` not found in chain `{self.__class__.__name__}`")

        index = node_name_or_index if isinstance(node_name_or_index, int) \
            else self._element_to_index_mapping[self._node_name_map[node_name_or_index]]
        if index < 0 or index >= len(self._element_list):
            raise IndexError(f"`node_or_index` is an out_of_bounds index: {index}")
        if index + 1 == len(self._element_list):
            raise ValueError(f"`node_or_index` is the last node in the chain `{self.__class__.__name__}`; unable to create empty chain!")

        for i in reversed(range(index + 1, len(self._element_list))):
            pass


    def fork(self) -> Self:
        pass

    def unify(self, index_or_node: int | Node, other_chain, other_index_or_node: int | Node) -> Self:
        pass

    def isolate(self, index_or_node: int | Node) -> Self:
        pass

    def get_all_parameters(self) -> list[str]:
        list_of_parameters = []
        for node in self._element_list:
            for param in node.get_parameters():
                list_of_parameters.append(f"{node.name}::{param.name}")
        return list_of_parameters

    def get_all_unused_outputs(self) -> list[str]:
        list_of_unused_outputs = []
        for node in self._element_list:
            for param in node.get_unused_outputs():
                list_of_unused_outputs.append(f"{node.name}::{param.name}")
        return list_of_unused_outputs

    @classmethod
    def join_chains(cls, leading_chain: Self, following_chain: Self, wiring: list[tuple[Sender, Receiver]]) -> Self:
        tail_node = leading_chain.get(leading_chain.get_tail_node_name())
        head_node = following_chain.get(following_chain.get_head_node_name())
        # confirm the chains are safe to join
        shared_names = set.intersection(set(leading_chain._node_name_map.keys()), set(following_chain._node_name_map.keys()))
        if 0 != len(shared_names):
            raise ValueError(f"Name collision: chains share nodes with the same name: `{repr(shared_names)}`")
        for receiver in head_node.get_input_list():
            if not receiver.has_source() or receiver.get_source_node() is tail_node:
                continue
            raise ValueError("Chains are not safe to join!")

        # perform the wiring first, so we can error out with a valid state
        Node.connect_to_dependency(tail_node, head_node, wiring)
        # perform transplant
        start_index = len(leading_chain._element_list)
        leading_chain._element_list += following_chain._element_list
        leading_chain._node_name_map.update(following_chain._node_name_map)
        for i in range(start_index, len(leading_chain._element_list)):
            leading_chain._element_to_index_mapping[leading_chain._element_list[i]] = i

# Standard starting chain for a pipeline
class Flow(Chain[Operation]):
    #TODO: see if we need / can add *args
    def __init__(self, start_node: type[Operation], node_name: str, chain_name: str = None):
        if not issubclass(start_node, Operation):
            raise TypeError(f"`starting_node` must be a *class* of sub-type of Operation, not `{start_node.__class__.__name__}`")
        super().__init__(start_node(node_name), chain_name)
        self._node_name_map: dict[str, Operation]

    def get(self, name: str) -> Operation:
        operation = super().get(name)
        if not isinstance(operation, Operation):
            raise RuntimeError(f"A non-operation node `{name}` was detected in chain `{self.__class__.__name__}`.")
        return operation

# Standard starting chain
class CollabThread(Chain):
    # TODO: see if we need / can add *args
    def __init__(self, start_node: type[Repetition], node_name: str, chain_name: str = None):
        if not issubclass(start_node, Repetition):
            raise TypeError(f"`starting_node` must be a sub-type of Repetition, not `{start_node.__class__.__name__}`")
        super().__init__(start_node(node_name), chain_name)

    def get_head(self):
        raise NotImplementedError()

    def get_operation(self, name: str) -> Operation:
        raise NotImplementedError()