from typing import Self, Any
from bscose.construction.chain import Chain, Flow
from bscose.construction.node import Operation, PatientOperation, Node, Sender, Receiver
from bscose.construction.parameter import ParameterSet

class Recipe:

    def __init__(self, name: str):
        if type(self) is Recipe:
            raise TypeError("Recipe cannot be instantiated directly, use one of it's children!")
        self._name = name
        self._chains: dict[str, Chain] = {}
        self._node_name_to_chain_names: dict[str, str] = {}
        self._chain_connections: dict[Chain, set[Chain]] = {}
        self._num_chain_ids_created: int = 0
        self.parameters: dict[str, Any] = {}
        #self._parameters = ParameterSet() # Save this for when we need speed down the line

    @property
    def name(self) -> str:
        return self._name

    def get(self, node_name: str) -> Node:
        if node_name not in self._node_name_to_chain_names:
            raise KeyError(f"{node_name} could not be found in the graph")
        return self._chains[self._node_name_to_chain_names[node_name]].get(node_name)

    def get_parameters(self, node: Node) -> list[str]:
        list_of_parameters = []
        for chain_id in self._chains:
            chain_params = self._chains[chain_id].get_all_parameters()
            augmented_parameter_list = [f"{node.name}({chain_id}).{param}" for param in chain_params]
            list_of_parameters.extend(augmented_parameter_list)
        return list_of_parameters

    def get_unused_outputs(self, node: Node) -> list[str]:
        list_of_unused_outputs = []
        for chain_id in self._chains:
            chain_params = self._chains[chain_id].get_all_parameters()
            augmented_parameter_list = [f"{node.name}({chain_id}).{param}" for param in chain_params]
            list_of_unused_outputs.extend(augmented_parameter_list)
        return list_of_unused_outputs

    # Export tools (maybe remove)
    def export_as_omex(self):
        pass

    def export_as_pbif(self):
        pass

    # def add_chain(self, chain):
    #     raise NotImplementedError("`addChain` is an abstract method, implemented by "
    #                               f"children of `{self.__class__.__name__}`")
    #
    # def remove_chain(self, chain):
    #     raise NotImplementedError("`removeChain` is an abstract method, implemented by "
    #                               f"children of `{self.__class__.__name__}`")

    # This function uses a tail-recursion design to generate a new id for a new chain
    def _generate_next_chain_id(self, _num: int | None = None, _existing_sequence: str | None = None) -> str:
        chain_chars = "αβγδεζηθικλμνξοπρστυφχψω"
        sequence = _existing_sequence if _existing_sequence is not None else ""
        num = _num if _num is not None else self._num_chain_ids_created
        divisor = len(chain_chars)
        div_res = num // divisor
        mod_res = num % divisor
        if div_res == 0:
            self._num_chain_ids_created += 1
            return sequence + chain_chars[mod_res]
        return self._generate_next_chain_id(divisor, sequence + chain_chars[mod_res])



class Pipeline(Recipe):

    def __init__(self, name: str):
        super().__init__(name)

    def get_new_node(self, node_type: type[Operation], node_name: str) -> Operation:
        if not issubclass(node_type, Operation):
            raise TypeError(f"Node type `{node_type}` is not a subclass of {Node.__class__.__name__}")
        if node_name in self._node_name_to_chain_names:
            raise ValueError(f"Node with name `{node_name}` already exists")
        # we build a chain, and the chain builds
        chain_id = self._generate_next_chain_id()
        new_chain = Flow(node_type, node_name, chain_id)
        new_node = new_chain.get(node_name)
        self._chains[chain_id] = new_chain
        self._node_name_to_chain_names[node_name] = chain_id
        self._chain_connections[new_chain] = set()
        return new_node

    def get(self, operation_name: str) -> Operation:
        if operation_name not in self._node_name_to_chain_names:
            raise KeyError(f"{operation_name} could not be found in the graph")
        result = self._chains[self._node_name_to_chain_names[operation_name]].get(operation_name)
        if not isinstance(result, Operation):
            raise RuntimeError(f"A non-Operation node was detected in a {self.__class__.__name__}. Contact the developers")
        return result

    def add_operation(self, operation_type: type[Operation], name: str, ):
        self.get_new_node(operation_type, name)
        return self

    def delete_operation(self, operation):
        raise NotImplementedError()

    def connect_nodes(self, output_node: str | Node, input_node: str | Node,
                      manual_wiring: list[tuple[str,str]] | None = None) -> Self:
        for node in [output_node, input_node]:
            if isinstance(node, str) and node not in self._node_name_to_chain_names:
                raise ValueError(f"Cannot find node with name `{node}` does not exist")
        # resolve to nodes
        output_var = output_node if isinstance(output_node, Node) \
            else self._chains[self._node_name_to_chain_names[output_node]].get(output_node)
        input_var = input_node if isinstance(input_node, Node) \
            else self._chains[self._node_name_to_chain_names[input_node]].get(input_node)

        # resolve wiring
        return self._connect_nodes(output_var, input_var, manual_wiring)

    def _connect_nodes(self, output_node: Node, input_node: Node,
                       manual_wiring: list[tuple[str,str]] | None = None):
        # first, check if we can even connect the nodes:
        if manual_wiring is None:
            wiring = Node.generate_autowired_mapping(output_node, input_node, skip_on_bound_receivers=True)
        else:
            wiring = Node.resolve_wiring_by_name(output_node, input_node, manual_wiring)
        if len(wiring) == 0:
            raise ValueError(f"Output Node {output_node.name} and input Node {input_node.name} cannot be automatically "
                             f"connected; check Receiver/Sender names and existing connections.")
        output_chain = self._chains[self._node_name_to_chain_names[output_node.name]]
        input_chain = self._chains[self._node_name_to_chain_names[input_node.name]]

        # check for special cases
        if output_chain is input_chain:
            return self._connect_nodes_within_same_chain(output_chain, output_node, input_node, wiring)
        if (output_chain.is_tail_node_with_no_targets(output_node.name)
                and input_chain.is_head_node_with_no_sources(input_node.name)):
            return self._merge_chains_and_connect_nodes(output_chain, input_chain, wiring)

        # Break down chains as needed
        if not output_chain.is_tail_node(output_node.name):
            # we need to split
            raise NotImplementedError()
        if not input_chain.is_head_node(input_node.name):
            # we need to split
            raise NotImplementedError()

        # We're ready, perform the connection
        return self._connect_head_to_tail_without_merge(output_chain, input_chain, wiring)

    def _connect_nodes_within_same_chain(self, chain: Chain, output_node: Node, input_node: Node, wiring: list[tuple[Sender, Receiver]]):
        raise NotImplementedError()

    def _merge_chains_and_connect_nodes(self, output_chain: Chain, input_chain: Chain, wiring: list[tuple[Sender, Receiver]]):
        for connection in self._chain_connections[output_chain]:
            if connection is input_chain:
                continue
            raise ValueError(f"Error: chain to append to (`{output_chain.name}`) has connections to "
                             f"chains other than `{input_chain.name}`")
        #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
        Chain.join_chains(output_chain, input_chain, wiring)
        #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
        self._chain_connections[output_chain] = self._chain_connections[input_chain]
        for key in self._node_name_to_chain_names:
            if self._node_name_to_chain_names[key] == input_chain.name:
                self._node_name_to_chain_names[key] = output_chain.name
        del self._chains[input_chain.name]

    def _connect_head_to_tail_without_merge(self, output_chain: Chain, input_chain: Chain, wiring: list[tuple[Sender, Receiver]]):
        raise NotImplementedError()

    def get_num_nodes(self):
        summation = 0
        for chain in self._chains.values():
            summation += chain.size()
        return summation

    def get_num_chains(self):
        return len(self._chains)

    def list_nodes(self):
        raise NotImplementedError()

    def list_chains(self):
        raise NotImplementedError()


class Collab(Recipe):
    pass
