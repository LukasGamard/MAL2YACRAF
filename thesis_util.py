import json
import copy
import logging
from tqdm import tqdm
from queue import SimpleQueue, LifoQueue
from general_gui import *
from thesis_constants import *

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def create_attack_graphs(model, attack_graph_file: str):
    """
    INPUTS: model - YACRAF Model instance
            attack_graph_file - name of a json file containing an attack graph from a compiled MAL DSL
    SIDE-EFFECT: instanciate a attack graphs, every asset on a new setup view
    """

    # read the file into a tree representation
    attack_trees : list[Tree] = file_to_trees(attack_graph_file)
    tree = attack_trees[0]
    print(f"{tree.size()=} {tree.width()=}")
    #a=1
    # generate the model
    tree_to_setup_view(model, tree)


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
        attack_steps = {str(attack_step[String.ID]): attack_step for name, attack_step in data[String.ATTACK_STEPS].items()}

    # inventory all unique asset names
    assets = set([attack_step[String.ASSET] for id, attack_step in attack_steps.items()])

    # for each asset, build full attack trees
    # start from a root and spread to children upon addition of any new node
    roots = [atk_step for id, atk_step in attack_steps.items() if not atk_step[String.PARENTS] and not atk_step[String.TYPE] == String.DEFENSE]
    defenses = [atk_step for id, atk_step in attack_steps.items() if atk_step[String.TYPE] == String.DEFENSE]

    trees = []
    start_position = (0,0)
    for root in roots:
        tree = Tree(start_position)
        tree.include_defenses(defenses, root[String.ASSET]) # need to add defenses BEFORE adding Nodes
        tree.root = Node(root, attack_steps, defenses=tree.defenses)
        tree.compute_grid_coordinates()
        start_position = (tree.get_width(), 0)
        trees.append(tree)

    return trees

def tree_to_setup_view(model, tree):
    setup_view = model.get_setup_views()[0]
    configuration_view_main = model.get_configuration_views()[Metamodel.YACRAF_1]
    configuration_classes_gui_main = configuration_view_main.get_configuration_classes_gui()
    tree.root.create_setup_class(setup_view, configuration_classes_gui_main)
    for defense in tree.defenses:
        defense.create_setup_class(setup_view, configuration_classes_gui_main)
    

class Tree():
    def __init__(self, position):
        self.root: Node = None
        self.defenses = list[Node]()
        self.position = position
        self.__width = 1

    def compute_grid_coordinates(self):
        self.root.compute_children_grid_coordinates(self.position)
        for i, defense in enumerate(self.defenses):
            defense.grid_position = (-Units.DEFENSE_MECHANISM_WIDTH - 2 * Units.HORIZONTAL_PADDING, i * (Units.DEFENSE_MECHANISM_HEIGHT + Units.VERTICAL_PADDING))

    def include_defenses(self, defenses, asset):
        if self.root:
            raise TreeBuildError("Defenses should be added before building the tree.")
        for defense in defenses:
            # Only include defenses that are for the same asset
            if not defense[String.ASSET] == asset:
                continue
            self.defenses.append(Node(defense, isDefense=True))

    def get_width(self):
        return self.__width
    
    def debug_print(self):
        fifo = SimpleQueue()
        fifo.put(self.root)
        fifo.put(String.NEWLINE)
        previous_node : Node = self.root
        file = open("debug.txt", "w")
        while not fifo.empty():
            node = fifo.get()
            if node == String.NEWLINE:
                print(file=file)
                continue
            for child in node.children_nodes:
                fifo.put(child)
            fifo.put(String.NEWLINE)
            print(" "*max(0, node.grid_position[0]-previous_node.grid_position[0]) + f"{node.attack_step["id"]:3d}", end="", file=file)
            previous_node = node
        file.close()

    # Iterable not needed any longer
    """
    def __iter__(self):
        self.__nodes = SimpleQueue()
        self.__nodes.put(self.root)
        self.__count = COUNT
        return self
    
    def __next__(self):
        if not self.__nodes.empty() and self.__count > 0:
            self.__count -= 1
            node : Node = self.__nodes.get()
            for child in node.children_nodes:
                self.__nodes.put(child)
            return node
        raise StopIteration
    """
    
    def size(self):
        return self.root.size()
    
    def width(self):
        return self.root.width()

class Node():
    def __init__(self, attack_step, attack_steps=None, ancestors=[], isDefense=False, defenses=None):
        self.attack_step = attack_step
        self.children_nodes = []
        self.ancestors = ancestors
        defense : Node
        if isDefense:
            return # TODO add children
        
        for defense in defenses:
            # Look for a defense mechanism for this attack step
            if str(self.attack_step[String.ID]) in defense.attack_step[String.CHILDREN]:
                defense.children_nodes.append(self)
        if self.attack_step[String.CHILDREN]:
            self.__add_children_nodes(attack_steps, defenses)

    def __add_children_nodes(self, attack_steps, defenses):
        """recursive bottom-up process to pull and connect children attack_steps"""
        # base case: no children
        for id, name in self.attack_step[String.CHILDREN].items():
            #print(f"child_id = {id}")
            if self.ancestors and int(id) in self.ancestors:
                # handle loops
                return
            ancestors : list = copy.deepcopy(self.ancestors)
            ancestors.append(self.attack_step[String.ID])
            child = Node(attack_steps[id], attack_steps, ancestors=ancestors, defenses=defenses)
            self.children_nodes.append(child)
    
    def __repr__(self):
        return f"{self.attack_step[String.ID]}"
    
    def __str__(self):
        return f"{self.attack_step[String.ID]}"

    def compute_children_grid_coordinates(self, position):
        """
        Place every node in a grid. Every level is left-justified. The root is on top.
        Depth-first 'in-order' algorithm
        INPUT: position assigned to the current Node
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position
        if not self.children_nodes:
            next_spot_on_same_row = (self.grid_position[0] + Units.ATTACK_EVENT_WIDTH + Units.HORIZONTAL_PADDING, self.grid_position[1])
            return next_spot_on_same_row
        child_node: Node
        child_position = (self.grid_position[0], self.grid_position[1] + Units.ATTACK_EVENT_HEIGHT + Units.VERTICAL_PADDING)
        for child_node in self.children_nodes:
            child_position = child_node.compute_children_grid_coordinates(child_position)
        next_spot_on_same_row = (child_position[0] + Units.HORIZONTAL_PADDING, self.grid_position[1])
        return next_spot_on_same_row
    
    def create_setup_class(self, setup_view, configuration_classes_gui):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        type = self.attack_step[String.TYPE]
        position = self.grid_position
        block : GUISetupClass
        if type == String.AND:
            block = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_AND], position=position)
        elif type == String.OR:
            block = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_OR], position=position)
        elif type == String.DEFENSE:
            block = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.DEFENSE_MECHANISM], position=position)
        block.set_name(self.attack_step[String.NAME])
        block.update_text()
        attributes = block.get_setup_attributes_gui()
        if type == String.AND or type == String.OR:
            attributes[Attack_event_setup_attribute.LOCAL_DIFFICULTY].set_entry_value("1/2/3") # TODO adapt to actual value

        # Create its children blocks
        child : Node
        for child in self.children_nodes:
            if not type == String.DEFENSE:
                child.create_setup_class(setup_view, configuration_classes_gui)
                top_left_corner = (self.grid_position[0] - 1, self.grid_position[1] + 0.25)
                child_top_right_corner = (child.grid_position[0] + Units.ATTACK_EVENT_WIDTH, child.grid_position[1] + 0.25)
                setup_view.create_connection_with_blocks(start_coordinate=child_top_right_corner, end_coordinate=top_left_corner)
            else:
                top_right_corner = (self.grid_position[0] + Units.ATTACK_EVENT_WIDTH, self.grid_position[1] + 0.25)
                child_top_left_corner = (child.grid_position[0] - 1, child.grid_position[1] + 0.25)
                setup_view.create_connection_with_blocks(start_coordinate=top_right_corner, end_coordinate=child_top_left_corner)

    def size(self):
        if not self.children_nodes:
            return 1
        return 1 + sum([child.size() for child in self.children_nodes])
    
    def width(self):
        if not self.children_nodes:
            return self.grid_position[0]
        return max([child.width() for child in self.children_nodes])
    
class TreeBuildError(Exception):
    """Raised when the defenses are added after the tree is built"""
    pass