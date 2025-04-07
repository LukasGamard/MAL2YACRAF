# allow forward references for type hints
from __future__ import annotations

import json
import copy
import logging
from tqdm import tqdm
from queue import SimpleQueue, LifoQueue
from blocks_gui.setup.setup_class_gui import GUISetupClass
from views.setup_view import SetupView
from views.configuration_view import ConfigurationView
from blocks_gui.configuration.configuration_class_gui import GUIConfigurationClass
from model import Model
from blocks_gui.general_gui import *
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

def parse_json(filename: str):
    """
    INPUTS: path to attack_graph.json
    OUTPUTS: parsed json ojects representing the different items present in attack_graph.json
    """
    with open(filename) as file:
        data = json.load(file)       
        # The json file is a list of attack_steps, each with its children
        # We want to reorganize this into a tree

        # create a dictionary "id": "attack_step", keeping childless nodes separate
        # use str() because children ids are strings, avoids later typecast
        attack_steps = {str(attack_step[String.ID]): attack_step for name, attack_step in data[String.ATTACK_STEPS].items()}
        attackers = {str(attacker[String.ID]): attacker for name, attacker in data[String.ATTACKERS].items()}
        abuse_cases = {str(abuse_case[String.ID]): abuse_case for name, abuse_case in data[String.ABUSE_CASES].items()}
        loss_events = {str(loss_event[String.ID]): loss_event for name, loss_event in data[String.LOSS_EVENTS].items()}
        actors = {str(actor[String.ID]): actor for name, actor in data[String.ACTORS].items()}
 
    return attack_steps, attackers, abuse_cases, loss_events, actors

def file_to_trees(filename: str) -> list:
    """
    INPUTS: filename - name of a yaml file containing an attack graph from a compiled MAL DSL
    OUTPUT: a tree representation of the attack graph
    """

    attack_steps, attackers, abuse_cases, loss_events, actors = parse_json(filename)

    # inventory all unique asset names
    assets = set([attack_step[String.ASSET] for id, attack_step in attack_steps.items()])

    # for each asset, build full attack trees
    # start from a root and spread to children upon addition of any new node
    roots = [atk_step for id, atk_step in attack_steps.items() if not atk_step[String.PARENTS] and not atk_step[String.TYPE] == String.DEFENSE]
    defenses = [atk_step for id, atk_step in attack_steps.items() if atk_step[String.TYPE] == String.DEFENSE]

    trees = []
    start_position = (0,0)
    for root in roots:
        related_abuse_cases = [abuse_case for id, abuse_case in abuse_cases.items() if root[String.ID] in abuse_case[String.ATTACK_STEPS]]
        related_loss_events = [loss_event for id, loss_event in loss_events.items() if root[String.ID] in loss_event[String.ATTACK_STEPS]]
        tree = Tree(start_position, related_abuse_cases, related_loss_events)
        tree.include_defenses(defenses, root[String.ASSET]) # need to add defenses BEFORE adding Nodes
        tree.root = Node(root, attack_steps, defenses=tree.defenses)
        tree.compute_grid_coordinates()
        start_position = (tree.get_width(), 0)
        trees.append(tree)

    return trees

def tree_to_setup_view(model: Model, tree: Tree):
    setup_view_attack_graph = model.get_setup_views()[0]
    setup_view_defenses = model.get_setup_views()[1]
    configuration_view_main : ConfigurationView = model.get_configuration_views()[Metamodel.YACRAF_1]
    configuration_classes_gui_main : list[GUIConfigurationClass]= configuration_view_main.get_configuration_classes_gui()
    tree.root.create_setup_class(setup_view_attack_graph, configuration_classes_gui_main)
    # TODO plot AC and LE

    # plot defenses in another setup view
    start_position = (0, 0)
    for defense in tree.defenses:
        defense.create_setup_class(setup_view_defenses, configuration_classes_gui_main, position=start_position, model=model)
        start_position = (start_position[0] + 2*Units.VERTICAL_PADDING + 2*Units.DEFENSE_MECHANISM_WIDTH, 0)
    
def set_default_attribute_values(type, setup_class_gui):
    attributes = setup_class_gui.get_setup_attributes_gui()
    match type:
        case String.AND | String.OR:
            attributes[Attack_event_setup_attribute.LOCAL_DIFFICULTY].set_entry_value("1/2/3") # TODO adapt to actual value
            return
        case String.DEFENSE:
            attributes[Defense_setup_attribute.COST].set_entry_value("10/20/30")
            attributes[Defense_setup_attribute.IMPACT].set_entry_value("20/30/40")


class Tree():
    def __init__(self, position, abuse_cases, loss_events):
        self.root: Node = None
        self.defenses = list[Node]()
        self.position = position
        self.abuse_cases = [Node(abuse_case) for abuse_case in abuse_cases]
        self.loss_events = [Node(loss_event) for loss_event in loss_events]
        self.__width = 1

    def compute_grid_coordinates(self):
        self.root.compute_children_grid_coordinates(self.position)
        # stack abuse_cases and loss_events above the root
        for i, abuse_case in enumerate(self.abuse_cases):
            abuse_case.grid_position = (self.position[0] - Units.ABUSE_CASE_WIDTH - Units.HORIZONTAL_PADDING, self.position[1] - i*(Units.ABUSE_CASE_HEIGHT + Units.VERTICAL_PADDING))
        
        for i, loss_event in enumerate(self.loss_events):
            loss_event.grid_position = (self.position[0] + Units.HORIZONTAL_PADDING + Units.LOSS_EVENT_WIDTH, self.position[1] - i*(Units.LOSS_EVENT_HEIGHT + Units.VERTICAL_PADDING))
        
        for i, defense in enumerate(self.defenses):
            # position for plotting in a separate setup view
            defense.grid_position = (i*(Units.DEFENSE_MECHANISM_WIDTH + 2 * Units.HORIZONTAL_PADDING + Units.ATTACK_EVENT_WIDTH), 0)

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
    def __init__(self, attack_step, attack_steps=None, ancestors=[], children_nodes=[], defenses=None):
        # TODO rename attack_step
        self.attack_step = attack_step
        self.children_nodes = children_nodes
        self.ancestors = ancestors

        defense : Node
        if attack_step[String.TYPE] == String.DEFENSE:
            return
        
        if attack_step[String.TYPE] == (String.OR | String.AND):
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
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        type = self.attack_step[String.TYPE]
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        self.setup_class_gui : GUISetupClass
        if type == String.AND:
            self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_AND], position=position)
        elif type == String.OR:
            self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_OR], position=position)
        elif type == String.DEFENSE:
            self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.DEFENSE_MECHANISM], position=position)
        self.setup_class_gui.set_name(self.attack_step[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Create its children blocks
        child : Node
        if not type == String.DEFENSE:
            for child in self.children_nodes:
                child.create_setup_class(setup_view, configuration_classes_gui)
                top_left_corner = (self.grid_position[0] - 1, self.grid_position[1] + 0.25)
                child_top_right_corner = (child.grid_position[0] + Units.ATTACK_EVENT_WIDTH, child.grid_position[1] + 0.25)
                setup_view.create_connection_with_blocks(start_coordinate=child_top_right_corner, end_coordinate=top_left_corner)
        elif type == String.DEFENSE:
            start_position = (position[0] + Units.VERTICAL_PADDING + Units.DEFENSE_MECHANISM_WIDTH, position[1])
            top_right_corner = (position[0] + Units.DEFENSE_MECHANISM_WIDTH, position[1] + 0.25)
            for child in self.children_nodes:
                # stack the children
                linked_setup_class_gui = model.create_linked_setup_class_gui(child.setup_class_gui, setup_view, position=start_position)
                set_default_attribute_values(child.attack_step[String.TYPE], linked_setup_class_gui)
                child_top_left_corner = (start_position[0] - 1, start_position[1] + 0.25)
                setup_view.create_connection_with_blocks(start_coordinate=top_right_corner, end_coordinate=child_top_left_corner)
                start_position = (start_position[0], start_position[1] + Units.SIMPLE_VERTICAL_PADDING + Units.ATTACK_EVENT_HEIGHT)

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
