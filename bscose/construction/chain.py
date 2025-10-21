from bscose.construction.node import Node, Operation, PatientOperation, Repetition
from bscose.construction.port import Sender, Receiver
from typing import Self, TypeVar, Generic
SomeTypeOfNode = TypeVar("SomeTypeOfNode", bound=Node, contravariant=True)

#TODO: see if we need / can add *args to internal method

class Chain(Generic[SomeTypeOfNode]):
    def __init__(self, starting_node: Node, chain_name: str | None = None, _override_abstract_creation: bool = False) -> None:
        if self.__class__ == Chain and not _override_abstract_creation:
            error_msg = f"`{self.__class__.__name__}` is a shared-behavior class that should not be instantiated directly."
            raise NotImplementedError(error_msg)
        self._name: str = chain_name if chain_name is not None else self.__class__.__name__
        self._element_list = [starting_node]
        self._element_to_index_mapping = {starting_node: 0}
        self._node_name_map: dict[str, SomeTypeOfNode] = { starting_node.name: starting_node }

    @property
    def name(self) -> str:
        return self._name

    def get(self, name_or_index: str | int) -> Node:
        if isinstance(name_or_index, int):
            if name_or_index < 0 or name_or_index >= len(self._element_list):
                raise IndexError(f"Index out of bounds ( in {self.__class__.__name__} `{self.name}`): {name_or_index} "
                                 f"not between `0` and `<{len(self._element_list)}`.")
            return self._element_list[name_or_index]
        elif isinstance(name_or_index, str):
            if name_or_index not in self._node_name_map:
                raise ValueError(f"Node with name `{name_or_index}` does not exist")
            return self._node_name_map[name_or_index]
        else:
            raise TypeError(f"`{name_or_index}` must be an int or str")

    def get_index(self, name: str):
        if name not in self._node_name_map:
            raise ValueError(f"Node `{name}` was not found in {self.__class__.__name__} `{self.name}`.")
        return self._element_to_index_mapping[self._node_name_map[name]]

    def get_all_node_names(self) -> list[str]:
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

    def append(self, name: str, operation_type: type[Operation], *node_construction_args, **node_construction_kwargs) -> Self:
        if name in self._node_name_map:
            raise KeyError(f"Node `{name}` already exists in chain {self.__class__.__name__}")
        attachment_node = self._element_list[-1]
        new_node = operation_type(name, *node_construction_args, **node_construction_kwargs)
        try:
            Node.connect_to_dependency(attachment_node, new_node)
        except ValueError as e:
            raise ValueError(f"Unable to extend chain with node `{name}`", e)
        self._element_list.append(new_node)
        self._element_to_index_mapping[new_node] = len(self._element_list)
        self._node_name_map[name] = new_node

    def _append_without_connection(self, operation: Operation):
        if operation.name in self._node_name_map:
            raise KeyError(f"Node `{operation.name}` already exists in chain {self.__class__.__name__}")
        self._element_list.append(operation)
        self._element_to_index_mapping[operation] = len(self._element_list)
        self._node_name_map[operation.name] = operation

    def remove_with_everything_following(self, name: str, throw_if_not_found: bool = True) -> Self:
        if name not in self._node_name_map:
            if throw_if_not_found:
                raise ValueError(f"Node `{name}` not found in chain `{self.__class__.__name__}`")
            return Self # else, nothing to do
        try:
            self.split(name, "to_be_deleted")
        except ValueError as e:
            if throw_if_not_found:
                raise e
        except IndexError | TypeError as e:
            raise e # we still want to declare error in these cases

        # `split()` removed everything but the target node to delete; delete it now.
        del self._element_to_index_mapping[self._node_name_map[name]]
        del self._node_name_map[name]
        self._element_list.pop()
        return self

    """
    Splits at index, such that all *following* nodes become their own chain
    Returns the new, split-off chain
    """
    def split(self, node_name_or_index: str | int, new_chain_name: str) -> Self:
        if not isinstance(node_name_or_index, int) and not isinstance(node_name_or_index, str):
            raise TypeError("`node_or_index` must be an instance of `Node` or and integer index")

        if isinstance(node_name_or_index, str) and (node_name_or_index not in self._node_name_map
                                                    or self._node_name_map[node_name_or_index] not in self._element_to_index_mapping):
            raise ValueError(f"Node `{node_name_or_index}` not found in chain `{self.name}`")

        index = node_name_or_index if isinstance(node_name_or_index, int) \
            else self._element_to_index_mapping[self._node_name_map[node_name_or_index]]
        if index < 0 or index >= len(self._element_list):
            raise IndexError(f"`node_or_index` is an out_of_bounds index: {index}")
        if index + 1 == len(self._element_list):
            raise ValueError(f"`node_or_index` is the last node in the {self.__class__.__name__} `{self.name}`; unable to create empty chain!")
        if index == 0:
            raise ValueError(f"`node_or_index` is the first node in the {self.__class__.__name__} `{self.name}`; unable to create empty chain!")

        operations = [operation for operation in self._element_list[1:] if isinstance(operation, Operation)]
        if len(operations) + 1 != len(self._element_list):
            raise RuntimeError("Non-operation nodes found there way into non-zero indexes; contact the developers.")

        new_chain = Chain(operations[index], new_chain_name, _override_abstract_creation=True)
        for i in range(index + 1, len(operations)):
            new_chain._append_without_connection(operations[i])

        for i in range(index + 1, len(self._element_list)):
            del self._node_name_map[self._element_list[i].name]
            del self._element_to_index_mapping[self._element_list[i]]
        self._element_list = self._element_list[:(index + 1)]

        return Flow.downcast_chain_safely(new_chain)

    def unify(self, index_or_node: int | Node, other_chain, other_index_or_node: int | Node) -> Self:
        pass

    def isolate(self, index_or_node: int | Node) -> Self:
        pass

    def get_all_parameters(self) -> dict[Node, list[Receiver]]:
        all_parameters = { node: list(node.get_parameters()) for node in self._element_list }
        for param_list in all_parameters.values():
            param_list.sort(key=lambda param: param.name)
        return all_parameters

    def display_all_parameters(self) -> list[str]:
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

    def disp_chain(self):
        return f"{self.__class__.__name__} {self.name}"

    def disp_nodal_chain(self):
        return " -> ".join([f"{node.name}[{node.__class__.__name__}]" for node in self._element_list])

# Standard starting chain for a pipeline
class Flow(Chain[Operation]):
    #TODO: see if we need / can add *args
    def __init__(self, start_node: type[Operation], node_name: str, chain_name: str = None):
        if not issubclass(start_node, Operation):
            raise TypeError(f"`starting_node` must be a *class* of sub-type of Operation, not `{start_node.__class__.__name__}`")
        super().__init__(start_node(node_name), chain_name)

    def get(self, name: str) -> Operation:
        operation = super().get(name)
        if not isinstance(operation, Operation):
            raise RuntimeError(f"A non-operation node `{name}` was detected in chain `{self.name}`.")
        return operation

    @classmethod
    def downcast_chain_safely(cls, chain: Chain) -> Self:
        operations_to_transplant: list[Operation] = []
        for node in chain._element_list:
            if not isinstance(node, Operation):
                raise ValueError(f"Cannot safely downcast; provided chain (`{chain.name}`) contains a node (`{node.name}`) that is not an Operation or a child of an Operation.")
            operations_to_transplant.append(node)
        new_flow = Flow(type(operations_to_transplant[0]), "temporary")
        new_flow._name = chain.name
        new_flow._element_list = operations_to_transplant
        new_flow._element_to_index_mapping = chain._element_to_index_mapping
        new_flow._node_name_map = chain._node_name_map
        return new_flow

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