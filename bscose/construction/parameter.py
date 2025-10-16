
from bscose.construction.node import Node, Receiver, ParametersChangedEvent

class ParameterSet:
    def __init__(self) -> None:
        self._parameters: dict[Node, set[Receiver]] = {}
        self._subscription_ids: dict[Node, str] = {}

    @property
    def parameters(self) -> dict[Node, set[Receiver]]:
        return dict(self._parameters) # Make a copy to protect the organization here

    def unsubscribe_from_node(self, node: Node) -> None:
        if node not in self._parameters:
            return
        node.parameter_change_announcer.remove_subscription(self._subscription_ids[node])
        del self._parameters[node]

    def update(self, event: ParametersChangedEvent) -> None:
        if event.node not in self._parameters:
            return
        self._parameters[event.node] = event.node.get_parameters()

    def subscribe_to_node(self, node: Node) -> None:
        subscriber_id = node.parameter_change_announcer.add_subscription(ParametersChangedEvent, self.update)
        self._parameters[node] = node.get_parameters()
        self._subscription_ids[node] = subscriber_id