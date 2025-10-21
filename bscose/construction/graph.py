from typing import Self, Any
from bscose.construction.chain import Chain, Flow
from bscose.construction.node import Operation, PatientOperation, Node, Sender, Receiver
from bscose.construction.parameter import ParameterSet
from bscose.construction.util import DisplayFormatter

class Recipe:

    def __init__(self, name: str):
        if type(self) is Recipe:
            raise TypeError("Recipe cannot be instantiated directly, use one of it's children!")
        self._name = name
        self._chains: dict[str, Chain] = {}
        self._node_name_to_chain_names: dict[str, str] = {}
        self._chain_connections: dict[Chain, set[Chain]] = {}
        self._num_chain_ids_created: int = 0
        self.parameters: dict[Chain, dict[Node, dict[Receiver, Any]]] = {}
        #self._parameters = ParameterSet() # Save this for when we need speed down the line

    @property
    def name(self) -> str:
        return self._name

    def get(self, node_name: str) -> Node:
        if node_name not in self._node_name_to_chain_names:
            raise KeyError(f"{node_name} could not be found in the graph")
        return self._chains[self._node_name_to_chain_names[node_name]].get(node_name)

    def get_all_parameters(self) -> dict[Chain, dict[Node, list[Receiver]]]:
        return { self._chains[chain]: self._chains[chain].get_all_parameters() for chain in self._chains }

    def get_all_parameters_to_display(self) -> set[str]:
        parameters_strings = set()
        for chain in self.parameters:
            for node in [chain.get(node_name) for node_name in chain.get_all_node_names()]:
                for param in node.get_parameters():
                    if param not in self.parameters[chain][node]:
                        continue
                    value = self.parameters[chain][node][param]
                    parameters_strings.add(f"\"{chain.name}.{node.name}::{param.name}\" = `{str(value)}`")
        return parameters_strings

    def set_parameter(self, node_name: str, parameter_name: str, value: Any):
        if node_name not in self._node_name_to_chain_names:
            raise KeyError(f"{node_name} could not be found in the graph")
        chain = self._chains[self._node_name_to_chain_names[node_name]]
        if chain not in self.parameters:
            self.parameters[chain] = {}
        node = chain.get(node_name)
        if node not in self.parameters[chain]:
            self.parameters[chain][node] = {}
        for receiver in node.get_input_list():
            if receiver.name == parameter_name:
                self.parameters[chain][node][receiver] = value


    def get_unused_outputs(self, node: Node) -> list[str]:
        list_of_unused_outputs = []
        for chain_id in self._chains:
            chain_params = self._chains[chain_id].display_all_parameters()
            augmented_parameter_list = [f"{node.name}({chain_id}).{param}" for param in chain_params]
            list_of_unused_outputs.extend(augmented_parameter_list)
        return list_of_unused_outputs


    def generate_representation(self) -> str:
        header = f"experiment \"{self.name}\":"
        chain_section_formatter = DisplayFormatter()
        for chain in self._chains.values():
            chain_declaration_section = f"{chain.__class__.__name__} {chain.name}:\t"
            nodes_in_chain_section = chain.disp_nodal_chain()
            chain_connections = list(self._chain_connections[chain])
            chain_connections.sort()
            chain_connections_section = f"| ({', '.join([chain.name for chain in chain_connections])})"
            chain_section_formatter.add_parts(chain_declaration_section, nodes_in_chain_section, chain_connections_section)
        connections_section = "\tconnections: \n\t\t"+ "\n\t\t".join(chain_section_formatter.get_parts_formatted())

        parameters_strings = sorted(self.get_all_parameters_to_display())

        parameters_section = "\tparameters: \n\t\t"+ "\n\t\t".join(parameters_strings) if len(parameters_strings) != 0 \
            else "\tparameters: DEFAULTS"

        chain_section_subsections: list[list[str]] = []
        sorted_chain_names = list(self._chains.keys())
        sorted_chain_names.sort()
        parameters = self.get_all_parameters()
        for chain_name in sorted_chain_names:
            chain: Chain = self._chains[chain_name]
            node_section_subsections: list[list[str]] = []
            sorted_node_names = chain.get_all_node_names()
            sorted_node_names.sort()
            for node_name in sorted_node_names:
                node = chain.get(node_name)
                ports_section_formatter = DisplayFormatter()
                sorted_receivers = node.get_input_list()
                sorted_receivers.sort(key=lambda r: r.name)
                for receiver in sorted_receivers:
                    param_str = ' - DEFAULT' if not self._has_parameter(chain,node,receiver) \
                        else f' = "{self._get_parameter(chain,node,receiver)}"'
                    connection_str = f"SOURCE = {receiver.get_source_node().name}::{receiver.get_source_sender().name}" \
                        if receiver.has_source() else f"PARAMETER" + param_str

                    receiver_prefix = f"{receiver.__class__.__name__} {receiver.name}:\t"
                    data_type_breakdown = f"{str(receiver.type)}"
                    connection_suffix = f"||\t{connection_str}"
                    ports_section_formatter.add_parts(receiver_prefix, data_type_breakdown, connection_suffix)
                sorted_senders = node.get_output_list()
                sorted_senders.sort(key=lambda r: r.name)
                for sender in sorted_senders:
                    connection_str: str
                    if not sender.has_connections():
                        connection_str = "(IGNORED)"
                    else:
                        targets = [f"{pair[0].name}({pair[1].name})" for pair in sender.get_sorted_targets()]
                        connection_str = f"[ {', '.join(targets)} ]"

                    sender_prefix = f"{sender.__class__.__name__} {sender.name}:\t"
                    data_type_breakdown = f"{str(sender.type)}"
                    connection_suffix = f"||\t{connection_str}"
                    ports_section_formatter.add_parts(sender_prefix, data_type_breakdown, connection_suffix)
                node_subsections = [f"Node {node.name}:"] + ["\t" + line for line in ports_section_formatter.get_parts_formatted()]
                node_section_subsections.append(node_subsections)
            all_node_lines: list[str] = []
            for subsection in node_section_subsections:
                for line_in_subsection in subsection:
                    all_node_lines.append(line_in_subsection)
                all_node_lines.append("")
            all_node_lines = all_node_lines[:-1]

            chain_subsection = [f"Chain: {chain.name}"] + ["\t" + line for line in all_node_lines]
            chain_section_subsections.append(chain_subsection)
        all_chain_lines: list[str] = []
        for subsection in chain_section_subsections:
            for line_in_subsection in subsection:
                all_chain_lines.append(line_in_subsection)
            all_chain_lines.append("")
        all_chain_lines = all_chain_lines[:-1]
        definitions_sections = "\tdefinitions: \n\t\t" + "\n\t\t".join(all_chain_lines)
        return "\n".join([header, connections_section, parameters_section, definitions_sections])


    def get_num_nodes(self):
        summation = 0
        for chain in self._chains.values():
            summation += chain.size()
        return summation

    def get_num_chains(self):
        return len(self._chains)

    def list_chains(self):
        raise NotImplementedError()

    def _add_new_chain(self, chain: Chain):
        if chain.name in self._chains:
            raise KeyError(f"{chain.name} already exists in the graph")
        self._chains[chain.name] = chain
        for node_name in chain.get_all_node_names():
            self._node_name_to_chain_names[node_name] = chain.name
        self._chain_connections[chain] = set()

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

    def _has_parameter(self, chain: Chain, node: Node, receiver: Receiver) -> bool:
        if chain not in self.parameters:
            return False
        if node not in self.parameters[chain]:
            return False
        if receiver not in self.parameters[chain][node]:
            return False
        return True

    def _get_parameter(self, chain: Chain, node: Node, receiver: Receiver) -> Any:
        if chain not in self.parameters:
            raise KeyError(f"{chain.name} does not exist in the {self.__class__.__name__} `{self.name}`.")
        if node not in self.parameters[chain]:
            raise KeyError(f"{node.name} does not exist in the {chain.__class__.__name__} `{chain.name}` in the {self.__class__.__name__} `{self.name}`.")
        if receiver not in self.parameters[chain][node]:
            raise KeyError(f"{receiver.name} does not exist in the {node.__class__.__name__} `{node.name}`  in the {chain.__class__.__name__} `{chain.name}` in the {self.__class__.__name__} `{self.name}`.")
        return self.parameters[chain][node][receiver]

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
        self._add_new_chain(new_chain)
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
            new_flow = output_chain.split(output_node.name, self._generate_next_chain_id())
            self._add_new_chain(new_flow)
            self._chain_connections[output_chain].add(new_flow)
        if not input_chain.is_head_node(input_node.name):
            # we don't want to only split away stuff after the input node, we want to split it too!
            new_target_index = input_chain.get_index(input_node.name) - 1
            new_flow = input_chain.split(input_chain.get(new_target_index).name, self._generate_next_chain_id())
            self._add_new_chain(new_flow)
            self._chain_connections[input_chain].add(new_flow)
            input_chain = new_flow

        # We're ready, perform the connection
        return self._connect_tail_to_head_without_merge(output_chain, input_chain, wiring)

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
        # Post-merge administration
        self._chain_connections[output_chain] = self._chain_connections[input_chain]
        for key in self._node_name_to_chain_names:
            if self._node_name_to_chain_names[key] == input_chain.name:
                self._node_name_to_chain_names[key] = output_chain.name
        del self._chains[input_chain.name]

    def _connect_tail_to_head_without_merge(self, output_chain: Chain, input_chain: Chain, wiring: list[tuple[Sender, Receiver]]):
        tail = output_chain.get(output_chain.get_tail_node_name())
        head = input_chain.get(input_chain.get_head_node_name())
        Node.connect_to_dependency(tail, head, wiring)
        self._chain_connections[output_chain].add(input_chain)



class Collab(Recipe):
    pass
