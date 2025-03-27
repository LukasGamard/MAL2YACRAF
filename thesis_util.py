import json
import collections
from queue import SimpleQueue

def create_attack_graph(model, attack_graph_file: str):
    """
    INPUTS: model - YACRAF Model instance
            attack_graph_file - name of a json file containing an attack graph from a compiled MAL DSL
    SIDE-EFFECT: instanciate a attack graphs, every asset on a new setup view
    """

    # read the file into a tree representation
    attack_trees : list[Tree] = file_to_trees(attack_graph_file)
    attack_trees[0].debug_print()
    # generate the model
    #tree_to_setup_view(model, attack_tree)


def file_to_trees(filename: str) -> list:
    """
    INPUTS: filename - name of a yaml file containing an attack graph from a compiled MAL DSL
    OUTPUT: a tree representation of the attack graph
    """

    with open(filename) as file:
        data = json.load(file)       
        # The json file is a list of attack_steps, each with its children
        # We want to reorganize this into a tree

        # create a dictionary "id": "attack_step", keeping childless nodes separate
        # use str() because children ids are strings, avoids later typecast
        attack_steps = {str(attack_step["id"]): attack_step for name, attack_step in data["attack_steps"].items()}

    # inventory all unique asset names
    assets = set([attack_step["asset"] for id, attack_step in attack_steps.items()])

    # for each asset, build full attack trees
    # start from a root and spread to children upon addition of any new node
    roots = [atk_step for id, atk_step in attack_steps.items() if not atk_step["parents"] and not atk_step["type"] == "defense"]
    # TODO what to do with defense nodes?

    trees = []
    start_position = (0,0)
    for root in roots:
        tree = Tree(Node(root, attack_steps), position=start_position)
        tree.compute_grid_coordinates()
        start_position = (tree.get_width(), 0)

    return trees

class Tree():
    def __init__(self, node, position=None):
        self.root: Node = node
        self.position = position
        self.__width = 1

    def compute_grid_coordinates(self):
        next_available_position = self.root.__compute_children_grid_coordinates(self.position)
        self.__width = next_available_position[0] - self.__width

    def get_width(self):
        return self.__width
    
    def debug_print(self):
        fifo = SimpleQueue()
        fifo.put(self.root)
        previous_node : Node = self.root
        while fifo:
            print()
            node : Node = fifo.get()
            for child in node.children_nodes:
                fifo.put(child)
            print(" "*(node.grid_position[0]-previous_node.grid_position[0]) + "x", end="")
            previous_node = node


class Node():
    def __init__(self, attack_step, attack_steps=None):
        self.attack_step = attack_step
        self.children_nodes = []
        if self.attack_step["children"]:
            self.__add_children_nodes(attack_steps)

    def __add_children_nodes(self, attack_steps):
        """recursive bottom-up process to pull and connect children attack_steps"""
        # base case: no children
        for id, name in self.attack_step["children"].items():
            print(f"child_id = {id}")
            self.children_nodes.append(Node(attack_steps[id], attack_steps))
            # TODO: problem, there can be loops...

    def __compute_children_grid_coordinates(self, position):
        """
        Place every node in a grid. Every level is left-justified. The root is on top.
        Depth-first 'in-order' algorithm
        INPUT: position assigned to the current Node
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position
        if not self.children_nodes:
            next_spot_on_same_row = (position[0] + 1, position[1])
            return next_spot_on_same_row
        child_node: Node
        child_position = (self.grid_position[0], self.grid_position[1] - 1)
        for child_node in self.children_nodes:
            child_position = child_node.__compute_children_grid_coordinates(child_position)
        next_spot_on_same_row = (child_position[0], child_position[1] + 1)
        return next_spot_on_same_row