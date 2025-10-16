import pytest
from bscose.construction.graph import Pipeline
from bscose.example_nodes.math_examples import Increment
from bscose.construction.node import Operation

def test_nodes_can_be_added():
    graph = Pipeline("graph_with_nodes_added")
    graph.add_operation(Increment, "A", )
    assert graph.get_num_nodes() == 1
    graph.add_operation(Increment, "B")
    assert graph.get_num_nodes() == 2

def test_nodes_can_connected():
    graph: Pipeline = Pipeline("graph_with_nodes_added")
    a: Operation = graph.add_operation(Increment, "A", ).get("A")
    b: Operation = graph.add_operation(Increment, "B", ).get("B")
    assert graph.get_num_chains() == 2
    assert graph.get_num_nodes() == 2
    graph.connect_nodes("A", "B", [("result","value")])
    assert graph.get_num_chains() == 1
    assert graph.get_num_nodes() == 2
