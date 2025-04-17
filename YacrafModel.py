from __future__ import annotations
from abc import abstractmethod
from thesis_constants import *
from queue import SimpleQueue
from blocks_gui.setup.setup_class_gui import GUISetupClass
from blocks_gui.connection.connection_with_blocks_gui import GUIConnectionWithBlocks, GUIConnection
from views.setup_view import SetupView
from views.configuration_view import ConfigurationView
from blocks_gui.configuration.configuration_class_gui import GUIConfigurationClass
from typing import Any, Iterable, Iterator
import copy
from model import Model
 
def set_default_attribute_values(type, setup_class_gui):
    # TODO refactor into different classes
    attributes = setup_class_gui.get_setup_attributes_gui()
    match type:
        case String.AND | String.OR:
            attributes[Attack_event_setup_attribute.LOCAL_DIFFICULTY].set_entry_value("1/2/3") # TODO adapt to actual value
            return
        case String.DEFENSE:
            attributes[Defense_setup_attribute.COST].set_entry_value("10/20/30")
            attributes[Defense_setup_attribute.IMPACT].set_entry_value("20/30/40")

class YacrafModel:
    def __init__(self, attack_tree_roots, attack_events, defenses, abuse_cases, loss_events, attackers, actors):
        """
        Instantiate all elements in the YACRAF model
        Organize them in tree structures
        """
        # Recursively build the attack trees, adding children AttackEvents
        self.attack_trees = [AttackEvent(root, attack_events) for root in attack_tree_roots]
        # Recursively build the risk trees, adding children to each layer
        self.risk_trees = [Actor(actor, loss_events, abuse_cases, attackers) for actor in actors]
        # Build defense trees by linking the attack events to the defenses
        self.defenses = [Defense(defense, self.attack_trees) for defense in defenses]

    def plot(self, model: Model):
        # configuration classes defined in the yagraf model
        configuration_view : ConfigurationView = model.get_configuration_views()[Metamodel.YACRAF_1]
        configuration_classes_gui : list[GUIConfigurationClass]= configuration_view.get_configuration_classes_gui()
        
        ## Plot all attack trees
        # one view per tree
        # create setup_classes for AttackEvents
        setup_views_attack_tree : list[SetupView] = []
        for attack_tree in self.attack_trees:
            setup_view_attack_tree : SetupView = model.create_view(False, f"Attack Tree: {attack_tree.data[String.NAME]}")
            setup_views_attack_tree.append(setup_view_attack_tree)
            attack_tree.create_setup_class(setup_view_attack_tree, configuration_classes_gui, (0, 0))
            #setup_view_attack_tree.set_excluded(True) # don't want to show full attack trees
        
        ## Plot all defenses in the same view
        # create setup_classes for Defenses, linked_setup_classes for AttackEvents
        setup_view_defense : SetupView = model.create_view(False, f"Defense Mechanisms")
        for i, defense in enumerate(self.defenses):
            defense_position = (i*(Defense.width + AttackEvent.width + 2*Node.Padding.X), 0)
            defense.create_setup_class(setup_view_defense, configuration_classes_gui, defense_position, model)

        ## Plot the risk trees
        # one setup view per actor
        # create setup_classes for Actors, LossEvents, AbuseCases and Attackers
        for actor in self.risk_trees:
            setup_view_risk = model.create_view(False, f"Risk for {actor.data[String.NAME]}")
            actor.create_setup_class(setup_view_risk, configuration_classes_gui, (0, 0))
        
        ## Plot the abuse cases and loss events linked to the top of an attack tree
        for attack_tree in self.attack_trees:
            setup_view_attack_tree_top_level : SetupView = model.create_view(False, f"Abuse Cases/Loss Events for {attack_tree.data[String.NAME]}")
            start_position = (0, 0)
            # link the root of the attack tree
            linked_root : GUISetupClass = model.create_linked_setup_class_gui(attack_tree.setup_class_gui, setup_view_attack_tree_top_level, position=start_position)
            root_top_left_corner = Node.get_top_left_corner(start_position)
            root_top_right_corner = Node.get_top_right_corner(start_position)

            for risk_tree in self.risk_trees:
                # Plot abuse cases
                for i, abuse_case in enumerate(Actor.AbuseCaseIterable(risk_tree)):
                    abuse_case_position = (start_position[0] - AbuseCase.width - 2*Node.Padding.X, start_position[1] - (i+1)*(AbuseCase.height + Node.Padding.Y))
                    linked_abuse_case : GUISetupClass = model.create_linked_setup_class_gui(abuse_case.setup_class_gui, setup_view_attack_tree_top_level, position=abuse_case_position)
                    abuse_case_top_right_corner = Node.get_top_right_corner(abuse_case_position)
                    setup_view_attack_tree_top_level.create_connection_with_blocks(start_coordinate=abuse_case_top_right_corner, end_coordinate=root_top_left_corner)
                
                # Plot the loss events
                for i, loss_event in enumerate(Actor.LossEventIterable(risk_tree)):
                    loss_event_position = (start_position[0] + AttackEvent.width + 2*Node.Padding.X, start_position[1] - (i+1)*(LossEvent.height + Node.Padding.Y))
                    linked_loss_event : GUISetupClass = model.create_linked_setup_class_gui(loss_event.setup_class_gui, setup_view_attack_tree_top_level, position=loss_event_position)
                    loss_event_top_left_corner = Node.get_top_left_corner(loss_event_position)
                    setup_view_attack_tree_top_level.create_connection_with_blocks(start_coordinate=root_top_right_corner, end_coordinate=loss_event_top_left_corner)


        def isValid():
            # TODO verify that all multiplicities in YACRAF are satisfied
            return True
        
        # TODO remove?
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
                print(" "*max(0, node.grid_position[0]-previous_node.grid_position[0]) + f"{node.attack_event["id"]:3d}", end="", file=file)
                previous_node = node
            file.close()
        """
    def size(self):
        return self.__root.size()
    
    def width(self):
        return self.__root.width()
"""

class Node:
    """Base class for all nodes in the YACRAF model"""
    class Offset:
        """Offsets used for the connecting nodes"""
        X = 1.0
        Y = 0.25

    class Padding:
        """Padding used for the connecting nodes"""
        X = 2
        Y = 4

    width = 11
    height = 1

    def __init__(self, data):
        self.data : dict[str, Any] = data
        self.children : list[Node]
        self.setup_class_gui : GUISetupClass
        self.grid_position : tuple[float, float]

    def __repr__(self):
        return f"{self.__class__.__name__}:{self.data[String.ID]}"
    
    def __str__(self):
        return f"{self.data[String.ID]}"

    @abstractmethod
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        # Create eventual children blocks and connections       
        pass

    @staticmethod
    def get_top_left_corner(position):
        """Get the top left corner of the node in order to draw a connection"""
        return (position[0] - Node.Offset.X, position[1] + Node.Offset.Y)
    
    @staticmethod
    def get_top_right_corner(position):
        """Get the top right corner of the node in order to draw a connection"""
        return (position[0] + Node.width, position[1] + Node.Offset.Y)
    
    @staticmethod
    def get_top_middle(position):
        """Get the top middle of the node in order to draw a connection"""
        return (position[0] + Node.width/2, position[1] + Node.Offset.Y)
    
    @staticmethod
    def get_bottom_middle(position):
        """Get the bottom middle of the node in order to draw a connection"""
        return (position[0] + Node.width/2, position[1] + Node.height + Node.Offset.Y)
    
"""
    def size(self):
        if not self.children_nodes:
            return 1
        return 1 + sum([child.size() for child in self.children_nodes])
    
    def width(self):
        if not self.children_nodes:
            return self.grid_position[0]
        return max([child.width() for child in self.children_nodes])
"""

class AttackEvent(Node):
    """
    Class representing an attack event in the YACRAF model.
    Iterable on a subtree basis.
    """

    height = 5

    def __init__(self, data, attack_events, ancestors=None):
        """Recursively build the tree that has this Node as its root"""
        super().__init__(data)
        self.children : list[AttackEvent]= []
        self.ancestors : list[int] = ancestors

        if self.data[String.CHILDREN]:
            self.__add_children_nodes(attack_events)
    
    def __add_children_nodes(self, attack_events):
        """recursive bottom-up process to pull and connect children attack_events"""
        # base case: no children
        for id, name in self.data[String.CHILDREN].items():
            if self.ancestors and int(id) in self.ancestors:
                # avoid loops
                return
            ancestors : list = copy.deepcopy(self.ancestors) if self.ancestors else []
            ancestors.append(self.data[String.ID])
            child = AttackEvent(attack_events[id], attack_events, ancestors=ancestors)
            self.children.append(child)

    def __iter__(self):
        """Iterate over the subtree rooted and this AttackEvent in a breadth-first manner"""
        fifo = SimpleQueue()
        fifo.put(self)
        while not fifo.empty():
            node : AttackEvent = fifo.get()
            self.next = node
            for child in node.children:
                fifo.put(child)
            yield node

    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position, full_attack_tree=True) -> tuple[float, float]:
        """
        create the setup representation for the node and add connections to its children        
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position

        # Recursively build the tree "inorder", from the bottom up
        if full_attack_tree:

            if not self.children:
                # Create a visual block representation
                type = self.data[String.TYPE]
                if type == String.AND: # attack event AND
                    self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_AND], position=position)
                elif type == String.OR: # attack event OR
                    self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_OR], position=position)
                
                # Initialize its attribute values
                self.setup_class_gui.set_name(self.data[String.NAME])
                self.setup_class_gui.update_text()
                #set_default_attribute_values(type, self.setup_class_gui)

                next_spot_on_same_row = (position[0] + AttackEvent.width + Node.Padding.X, position[1])
                return next_spot_on_same_row
            
            # Plot children
            next_available_child_position = (position[0], position[1] + AttackEvent.height + Node.Padding.Y)
            for child in self.children:   
                next_available_child_position = child.create_setup_class(setup_view, configuration_classes_gui, position=next_available_child_position)              
                setup_view.create_connection_with_blocks(start_coordinate=child.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

        # Create a visual block representation
        type = self.data[String.TYPE]
        if type == String.AND:
            self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_AND], position=position)
        elif type == String.OR:
            self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_OR], position=position)
        # Initialize its attribute values
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()

        if full_attack_tree:
            next_spot_on_same_row = (next_available_child_position[0] + Node.Padding.X, position[1])
        else:
            next_spot_on_same_row = (position[0] + Node.Padding.X, position[1])
        return next_spot_on_same_row


    def get_top_left_corner(self):
        """Get the top left corner of the node in order to draw a connection"""
        return (self.grid_position[0] - Node.Offset.X, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_right_corner(self):
        """Get the top right corner of the node in order to draw a connection"""
        return (self.grid_position[0] + AttackEvent.width, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_middle(self):
        """Get the top middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] - Node.Offset.Y)
    
    def get_bottom_middle(self):
        """Get the bottom middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + AttackEvent.height - Node.Offset.Y)
  

class Defense(Node):
    height = 3

    def __init__(self, defense_data, attack_trees : list[AttackEvent]):
        super().__init__(defense_data)
        
        # Attack steps add themselves to this list upon instantiation
        self.children : list[AttackEvent] = []
        tree : Tree[AttackEvent]
        for tree in attack_trees:
            for attack_event in tree:
                if str(attack_event.data[String.ID]) in self.data[String.CHILDREN]:
                    self.children.append(attack_event)

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position, model : Model):
        """create the setup representation for the node and add connections to its children"""
        self.grid_position = position

        # Create a block
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.DEFENSE_MECHANISM], position=self.grid_position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Create eventual children blocks and connections
        next_available_child_position = (self.grid_position[0] + 2*Node.Padding.X + Defense.width, self.grid_position[1])
        top_right_corner = self.get_top_right_corner()
        for child in self.children:
            # stack the children
            linked_setup_class_gui = model.create_linked_setup_class_gui(child.setup_class_gui, setup_view, position=next_available_child_position)
            set_default_attribute_values(child.data[String.TYPE], linked_setup_class_gui)
            child_top_left_corner = Node.get_top_left_corner(next_available_child_position)
            setup_view.create_connection_with_blocks(start_coordinate=top_right_corner, end_coordinate=child_top_left_corner)
            next_available_child_position = (next_available_child_position[0], next_available_child_position[1] + Node.Padding.X + AttackEvent.height)

    def get_top_left_corner(self):
        """Get the top left corner of the node in order to draw a connection"""
        return (self.grid_position[0] - Node.Offset.X, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_right_corner(self):
        """Get the top right corner of the node in order to draw a connection"""
        return (self.grid_position[0] + Defense.width, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_middle(self):
        """Get the top middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.Offset.Y)
    
    def get_bottom_middle(self):
        """Get the bottom middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.height + Node.Offset.Y)


class Actor(Node):
    height = 3

    class AbuseCaseIterable(Iterable["AbuseCase"]):
        def __init__(self, actor_instance : Actor):
            self.actor_instance = actor_instance

        def __iter__(self) -> Iterator[AbuseCase]:
            return Actor.AbuseCaseIterator(self.actor_instance)
    
    class AbuseCaseIterator(Iterator["AbuseCase"]):
        def __init__(self, actor_instance : Actor):
            self.actor_instance = actor_instance
            self.fifo = SimpleQueue()
            for loss_event in self.actor_instance.children:
                for abuse_case in loss_event.children:
                    self.fifo.put(abuse_case)

        def __iter__(self) -> Iterator[AbuseCase]:
            return self
        
        def __next__(self):
            if not self.fifo.empty():
                return self.fifo.get()
            else:
                raise StopIteration

    class LossEventIterable(Iterable["LossEvent"]):
        def __init__(self, actor_instance : Actor):
            self.actor_instance = actor_instance

        def __iter__(self) -> Iterator[LossEvent]:
            return Actor.LossEventIterator(self.actor_instance)
        
    class LossEventIterator(Iterator["LossEvent"]):
        def __init__(self, actor_instance : Actor):
            self.actor_instance = actor_instance
            self.fifo = SimpleQueue()
            for loss_event in self.actor_instance.children:
                self.fifo.put(loss_event)

        def __iter__(self) -> Iterator[LossEvent]:
            return self

        def __next__(self):
            if not self.fifo.empty():
                return self.fifo.get()
            else:
                raise StopIteration

    def __init__(self, actor_data, loss_events_data, abuse_cases_data, attackers_data):
        super().__init__(actor_data)
        self.children = [LossEvent(loss_events_data[id], abuse_cases_data, attackers_data) for id in actor_data[String.LOSS_EVENTS].keys()]

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position):
        """
        In the context of a risk tree, create the setup representation for the node and add connections to its children
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position

        # Build the risk tree "inorder", from the bottom up
        # Plot children
        next_available_child_position = (position[0], position[1] + Actor.height + Node.Padding.Y)
        for child in self.children:   
            next_available_child_position = child.create_setup_class(setup_view, configuration_classes_gui, next_available_child_position)              
            setup_view.create_connection_with_blocks(start_coordinate=child.get_top_right_corner(), end_coordinate=self.get_top_left_corner())
        
        # Create a visual block representation
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ACTOR], position=position)
        # Initialize its attribute values 
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()

        next_spot_on_same_row = (next_available_child_position[0] + Node.Padding.X, position[1])
        return next_spot_on_same_row

    def get_top_left_corner(self):
        """Get the top left corner of the node in order to draw a connection"""
        return (self.grid_position[0] - Node.Offset.X, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_right_corner(self):
        """Get the top right corner of the node in order to draw a connection"""
        return (self.grid_position[0] + Actor.width, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_middle(self):
        """Get the top middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.Offset.Y)
    
    def get_bottom_middle(self):
        """Get the bottom middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.height + Node.Offset.Y)


class LossEvent(Node):
    height = 5

    def __init__(self, loss_event_data, abuse_cases_data, attackers_data):
        super().__init__(loss_event_data)
        self.children = [AbuseCase(abuse_cases_data[id], attackers_data) for id in loss_event_data[String.ABUSE_CASES].keys()]
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position):
        """In the contest of a risk tree, create the setup representation for the node and add connections to its children"""
        self.grid_position = position

        # Plot the children
        next_available_child_position = (position[0], position[1] + LossEvent.height + Node.Padding.Y)
        for child in self.children:
            next_available_child_position = child.create_setup_class(setup_view, configuration_classes_gui, next_available_child_position)
            setup_view.create_connection_with_blocks(start_coordinate=child.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

        # Create a block
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.LOSS_EVENT], position=self.grid_position)
        
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        #set_default_attribute_values(type, self.setup_class_gui)

        next_spot_on_same_row = (next_available_child_position[0] + Node.Padding.X, position[1])
        return next_spot_on_same_row
    
    def get_top_left_corner(self):
        """Get the top left corner of the node in order to draw a connection"""
        return (self.grid_position[0] - Node.Offset.X, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_right_corner(self):
        """Get the top right corner of the node in order to draw a connection"""
        return (self.grid_position[0] + LossEvent.width, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_middle(self):
        """Get the top middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.Offset.Y)
    
    def get_bottom_middle(self):
        """Get the bottom middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.height + Node.Offset.Y)


class AbuseCase(Node):
    height = 11

    def __init__(self, abuse_case_data, attackers_data):
        super().__init__(abuse_case_data)
        attacker_dict = abuse_case_data[String.ATTACKER]
        attacker_name = attacker_dict[next(iter(attacker_dict.keys()))]
        # NOTE: unhandy code because of the json format trying to be consistent with the previous format
        self.child = Attacker(attackers_data[attacker_name])

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position):
        """
        In the context of a risk tree, create the setup representation for the node and add connections to its children
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position

        # Plot the children
        next_available_child_position = (position[0], position[1] + AbuseCase.height + Node.Padding.Y)
        self.child.create_setup_class(setup_view, configuration_classes_gui, position=next_available_child_position)
        setup_view.create_connection_with_blocks(start_coordinate=self.child.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

        # Create a block
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ABUSE_CASE], position=position)
        
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Link Attacker in a tree structure
        attacker_position = (self.grid_position[0], self.grid_position[1] + AbuseCase.height + Node.Padding.Y)
        self.child.create_setup_class(setup_view, configuration_classes_gui, attacker_position)
        setup_view.create_connection_with_blocks(start_coordinate=self.child.get_top_right_corner(), end_coordinate=self.get_top_left_corner())
        next_spot_on_same_row = (self.grid_position[0] + AbuseCase.width + Node.Padding.X, self.grid_position[1])
        return next_spot_on_same_row

    def get_top_left_corner(self):
        """Get the top left corner of the node in order to draw a connection"""
        return (self.grid_position[0] - Node.Offset.X, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_right_corner(self):
        """Get the top right corner of the node in order to draw a connection"""
        return (self.grid_position[0] + AbuseCase.width, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_middle(self):
        """Get the top middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.Offset.Y)
    
    def get_bottom_middle(self):
        """Get the bottom middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.height + Node.Offset.Y)


class Attacker(Node):
    height = 7

    def __init__(self, attacker_data):
        super().__init__(attacker_data)
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position):
        """In the context of a risk tree, create the setup representation for the node and add connections to its children"""
        # Create a block
        self.grid_position = position
        
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACKER], position=position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        #set_default_attribute_values(self.setup_class_gui)

    def get_top_left_corner(self):
        """Get the top left corner of the node in order to draw a connection"""
        return (self.grid_position[0] - Node.Offset.X, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_right_corner(self):
        """Get the top right corner of the node in order to draw a connection"""
        return (self.grid_position[0] + Attacker.width, self.grid_position[1] + Node.Offset.Y)
    
    def get_top_middle(self):
        """Get the top middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.Offset.Y)
    
    def get_bottom_middle(self):
        """Get the bottom middle of the node in order to draw a connection"""
        return (self.grid_position[0] + Node.width/2, self.grid_position[1] + Node.height + Node.Offset.Y)


class YacrafModelBuildError(Exception):
    """Raised when the defenses are added after the tree is built"""
    pass
