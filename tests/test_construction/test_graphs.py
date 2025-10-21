from bscose.construction.graph import Pipeline
from bscose.example_nodes.math_examples import Increment, Addition
from bscose.construction.node import Operation

def test_connecting_nodes_across_chains():
    graph = Pipeline("Connecting nodes across chains")
    graph.add_operation(Increment, "A")
    graph.add_operation(Increment, "B")
    graph.add_operation(Increment, "C")
    graph.add_operation(Addition, "SUM")
    assert graph.get_num_chains() == 4
    graph.connect_nodes("A", "B", [("result","value")])
    graph.connect_nodes("B", "SUM", [("result","addend_1")])
    graph.connect_nodes("C", "SUM", [("result","addend_2")])
    assert graph.get_num_chains() == 3

def test_setting_and_getting_parameters():
    graph: Pipeline = Pipeline("graph_for_getting_setting_parameters")
    graph.add_operation(Addition, "A")
    graph.set_parameter("A", "addend_1", 3)
    graph.set_parameter("A", "addend_2", 4)
    params = graph.get_all_parameters_to_display()
    expected = {'"α.A::addend_1" = `3`', '"α.A::addend_2" = `4`'}
    assert params == expected


def test_representation():
    desired_representation = """
experiment "Connecting nodes across chains":
	connections: 
		Flow α:	A[Increment] -> B[Increment]| (ε)
		Flow γ:	C[Increment]                | (ε)
		Flow ε:	SUM[Addition]               | ()
	parameters: 
		"α.A::value" = `3`
		"γ.C::value" = `4`
	definitions: 
		Chain: α
			Node A:
				Receiver value:	[NoneUnit] of `|NoneClassification|`||	PARAMETER = "3"
				Sender result:	 [NoneUnit] of `|NoneClassification|`||	[ B(value) ]
			
			Node B:
				Receiver value:	[NoneUnit] of `|NoneClassification|`||	SOURCE = A::result
				Sender result:	 [NoneUnit] of `|NoneClassification|`||	[ SUM(addend_1) ]
		
		Chain: γ
			Node C:
				Receiver value:	[NoneUnit] of `|NoneClassification|`||	PARAMETER = "4"
				Sender result:	 [NoneUnit] of `|NoneClassification|`||	[ SUM(addend_2) ]
		
		Chain: ε
			Node SUM:
				Receiver addend_1:	[NoneUnit] of `|NoneClassification|`||	SOURCE = B::result
				Receiver addend_2:	[NoneUnit] of `|NoneClassification|`||	SOURCE = C::result
				Sender sum:	       [NoneUnit] of `|NoneClassification|`||	(IGNORED)
    """.strip()
    graph = Pipeline("Connecting nodes across chains")
    graph.add_operation(Increment, "A")
    graph.add_operation(Increment, "B")
    graph.add_operation(Increment, "C")
    graph.add_operation(Addition, "SUM")
    assert graph.get_num_chains() == 4
    graph.connect_nodes("A", "B", [("result", "value")])
    graph.connect_nodes("B", "SUM", [("result", "addend_1")])
    graph.connect_nodes("C", "SUM", [("result", "addend_2")])
    assert graph.get_num_chains() == 3
    graph.set_parameter("A", "value", 3)
    graph.set_parameter("C", "value", 4)
    representation = graph.generate_representation()
    assert representation == desired_representation

