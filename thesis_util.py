import json
import collections

def create_attack_graph(model, attack_graph_file):
    """
    INPUTS: model - YACRAF Model instance
            attack_graph_file - name of a json file containing an attack graph from a compiled MAL DSL
    SIDE-EFFECT: instanciate the attack graph on a new setup view
    """

    # read the file into a tree representation
    attack_tree = file_to_tree(attack_graph_file)
    a=1
    # generate the model
    #tree_to_setup_view(model, attack_tree)


def file_to_tree(filename):
    """
    INPUTS: filename - name of a yaml file containing an attack graph from a compiled MAL DSL
    OUTPUT: a tree representation of the attack graph
    """

    with open(filename) as file:
        data = json.load(file)
        parent_attack_steps = {}
        bottom_attack_steps = {}

        # create a dictionary "id": "attack_step", keeping childless nodes separate
        for name, attack_step in data["attack_steps"].items():
            if attack_step["children"]:
                parent_attack_steps[attack_step["id"]] = attack_step
            else:
                bottom_attack_steps[attack_step["id"]] = attack_step
        # The json file is a list of attack_steps, each with its children
        # We want to reorganize this into a tree
    
    # build attack_events into a single attack tree
    subtrees = {}

    attack_steps = collections.ChainMap(parent_attack_steps, bottom_attack_steps)
    # loop once through all candidate subtree_roots
    for parent_id, parent_attack_step in parent_attack_steps.items():
        # First, pick attack_steps and build corresponding subtrees
        subtree_root = Node(parent_attack_step, attack_steps)
        bottom_attack_steps[id] = subtree_root # we can use the subtree below another subtree

    assert len(bottom_attack_steps) == 1 # only one tree left
    final_id, final_tree = bottom_attack_steps.popitem()
    return final_tree

        
class Node():
    def __init__(self, attack_step, attack_steps=None):
        self.attack_step = attack_step
        self.children_nodes = []
        if attack_steps:
            self.__add_children_nodes(attack_steps)
            self.__add_parent_node(attack_steps)

    def __add_children_nodes(self, attack_steps):
        """recursive bottom-up process to pull and connect children attack_steps"""
        for id, name in self.attack_step["children"].items():
            self.children_nodes.append(Node(attack_steps.pop(id), attack_steps)) # remove the attack step from the dictionary

    def __add_parent_node(self, attack_steps):
        """recursive funtion to add the parent of a node"""