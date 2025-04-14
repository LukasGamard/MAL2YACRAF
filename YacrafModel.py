from abc import abstractmethod
from thesis_constants import *
from queue import SimpleQueue
from blocks_gui.setup.setup_class_gui import GUISetupClass
from views.setup_view import SetupView
from views.configuration_view import ConfigurationView
from blocks_gui.configuration.configuration_class_gui import GUIConfigurationClass
from typing import Any
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
    def __init__(self, defenses, abuse_cases, loss_events, attackers, actors):
        """Initialize the tree by positioning it on the screen and adding abuse cases and loss events"""
        self.attack_trees: list[AttackEvent] = []
        self.defenses = [Defense(defense) for defense in defenses]
        self.abuse_cases = [AbuseCase(abuse_case) for abuse_case in abuse_cases]
        self.loss_events = [LossEvent(loss_event) for loss_event in loss_events]
        self.attackers = [Attacker(attacker) for attacker in attackers]
        self.actors = [Actor(actor) for actor in actors]

    def build(self, attack_tree_roots, attack_events):
        """Build the YACRAF model by connecting all its components"""
        
        for root in attack_tree_roots:
            # Recursively build the attack tree, linking attack events and defense mechanisms
            self.attack_trees.append(AttackEvent(root, attack_events=attack_events, defenses=self.defenses))
        
        for abuse_case in self.abuse_cases:
            # link the abuse case to attack trees
            for attack_tree_root in self.attack_trees:
                if str(attack_tree_root.data[String.ID]) in abuse_case.data[String.ATTACK_STEPS]:
                    abuse_case.attack_events.append(attack_tree_root)
            # link attacker and abuse case
            id = next(iter(abuse_case.data[String.ATTACKER])) # one attacker per abuse case, json dict format
            for attacker in self.attackers:
                if str(attacker.data[String.ID]) == id:
                    abuse_case.attacker = attacker
                    attacker.abuse_cases.append(abuse_case)

        for loss_event in self.loss_events:
            # link the loss events to attack trees
            for attack_tree_root in self.attack_trees:
                if str(attack_tree_root.data[String.ID]) in loss_event.data[String.ATTACK_STEPS]:
                    loss_event.attack_events.append(attack_tree_root)
            # link the loss event and abuse cases
            for id, name in loss_event.data[String.ABUSE_CASES].items():
                for abuse_case in self.abuse_cases:
                    if str(abuse_case.data[String.ID]) == id:
                        loss_event.abuse_cases.append(abuse_case)
                        abuse_case.loss_events.append(loss_event)
            # link actors and loss events
            for id, name in loss_event.data[String.ACTOR].items():
                actor : Actor
                for actor in self.actors:
                    if str(actor.data[String.ID]) == id:
                        loss_event.actor = actor
                        actor.loss_events.append(loss_event)
                        break # only one actor per loss event

    def compute_grid_coordinates(self):
        """Compute the grid coordinates for the model's nodes"""
        # Recursively compute grid positions for the attack trees
        for attack_tree in self.attack_trees:
            start_position = (0, 0)
            attack_tree.compute_attack_tree_grid_coordinates(start_position)

        # Recursively compute grid positions for the risk tree
        for actor in self.actors:
            actor.compute_risk_tree_grid_coordinates()

        for i, defense in enumerate(self.defenses):
            # position for plotting in the defense mechanism view
            defense.grid_position = (i*(Defense.width + AttackEvent.width + 2*Node.Padding.X), 0)

    def plot(self, model: Model):
        # configuration classes defined in the yagraf model
        configuration_view : ConfigurationView = model.get_configuration_views()[Metamodel.YACRAF_1]
        configuration_classes_gui : list[GUIConfigurationClass]= configuration_view.get_configuration_classes_gui()
        
        setup_views_attack_tree : list[SetupView] = []
        for attack_tree in self.attack_trees:
            setup_view_attack_tree : SetupView = model.create_view(False, f"Attack Tree: {attack_tree.data[String.NAME]}")
            setup_views_attack_tree.append(setup_view_attack_tree)
            attack_tree.create_setup_class(setup_view_attack_tree, configuration_classes_gui)
        
        setup_views_defenses : list[SetupView] = []
        for defense in self.defenses:
            setup_view_defense : SetupView = model.create_view(False, f"Defense Mechanisms: {defense.data[String.NAME]}")
            setup_views_defenses.append(setup_view_defense)
            defense.create_setup_class(setup_view_defense, configuration_classes_gui, model=model)
        setup_view_defenses : SetupView = model.create_view(False, f"Defense Mechanisms: {self.__root.data[String.NAME]}")

        
        ## create the attack tree
        self.__root.create_setup_class(setup_view_attack_tree, configuration_classes_gui_main)

        ## plot the risk tree
        # one setup view per actor
        for actor in self.actors:
            setup_view_risk = model.create_view(False, f"Risk for {actor.data[String.NAME]}")
            actor.create_setup_class(setup_view_risk, configuration_classes_gui_main)
        
        # stack abuse cases and loss event above the attack tree
        root_top_left_corner = self.__root.get_top_left_corner()
        root_top_right_corner = self.__root.get_top_right_corner()
        for i, abuse_case in enumerate(self.abuse_cases):
            abuse_case_position = (self.__root.grid_position[0] - AbuseCase.width - 2*Node.Padding.X, self.__root.grid_position[1] - (i+1)*(AbuseCase.height + Node.Padding.Y))
            model.create_linked_setup_class_gui(abuse_case.setup_class_gui, setup_view_attack_tree, position=abuse_case_position)
            abuse_case_top_right_corner = Node.get_top_right_corner(abuse_case_position)
            setup_view_attack_tree.create_connection_with_blocks(start_coordinate=abuse_case_top_right_corner, end_coordinate=root_top_left_corner)

        for i, loss_event in enumerate(self.loss_events):
            loss_event_position = (self.__root.grid_position[0] + AttackEvent.width + 2*Node.Padding.X, self.__root.grid_position[1] - (i+1)*(LossEvent.height + Node.Padding.Y))
            model.create_linked_setup_class_gui(loss_event.setup_class_gui, setup_view_attack_tree, position=loss_event_position)
            loss_event_top_left_corner = Node.get_top_left_corner(loss_event_position)
            setup_view_attack_tree.create_connection_with_blocks(start_coordinate=root_top_right_corner, end_coordinate=loss_event_top_left_corner)


        ## plot defenses in another setup view
        for defense in self.defenses:
            defense.create_setup_class(setup_view_defenses, configuration_classes_gui_main, model=model)
        

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
        self.grid_position : tuple[int, int]= None
        self.setup_class_gui : GUISetupClass

    def __repr__(self):
        return f"{self.data[String.ID]}"
    
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
    height = 5

    def __init__(self, data, attack_events=None, ancestors=None, defenses=None):
        """Recursively build the tree that has this Node as its root"""
        super().__init__(data)
        self.children_attack_events : list[AttackEvent]= []
        self.ancestors : list[int] = ancestors if ancestors else []

        # Look for defense mechanisms for this attack step
        defense : Defense
        for defense in defenses:
            if str(self.data[String.ID]) in defense.data[String.CHILDREN]:
                defense.children_attack_events.append(self)

        if self.data[String.CHILDREN]:
            self.__add_children_nodes(attack_events, defenses)
    
    def __add_children_nodes(self, attack_events, defenses):
        """recursive bottom-up process to pull and connect children attack_events"""
        # base case: no children
        for id, name in self.data[String.CHILDREN].items():
            #print(f"child_id = {id}")
            if self.ancestors and int(id) in self.ancestors:
                # avoid loops
                return
            ancestors : list = copy.deepcopy(self.ancestors)
            ancestors.append(self.data[String.ID])
            child = AttackEvent(attack_events[id], attack_events, ancestors=ancestors, defenses=defenses)
            self.children_attack_events.append(child)

    def compute_attack_tree_grid_coordinates(self, position):
        """
        Place every node in a grid. Every level is left-justified. The root is on top.
        Depth-first 'in-order' algorithm
        INPUT: position assigned to the current Node
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position
        if not self.children_attack_events:
            next_spot_on_same_row = (self.grid_position[0] + AttackEvent.width + Node.Padding.X, self.grid_position[1])
            return next_spot_on_same_row
        next_available_child_position = (self.grid_position[0], self.grid_position[1] + AttackEvent.height + Node.Padding.Y)
        for child_node in self.children_attack_events:
            next_available_child_position = child_node.compute_attack_tree_grid_coordinates(next_available_child_position)
        next_spot_on_same_row = (next_available_child_position[0] + Node.Padding.X, self.grid_position[1])
        return next_spot_on_same_row
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        type = self.data[String.TYPE]
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        
        if type == String.AND: # attack event AND
            self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_AND], position=position)
        elif type == String.OR: # attack event OR
            self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_OR], position=position)
        
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Create eventual children blocks and connections
        child : AttackEvent
        for child in self.children_attack_events:
            child.create_setup_class(setup_view, configuration_classes_gui)
            setup_view.create_connection_with_blocks(start_coordinate=child.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

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

    def __init__(self, data):
        super().__init__(data)
        
        # Attack steps add themselves to this list upon instantiation
        self.children_attack_events : list[AttackEvent] = []

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], model : Model=None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.DEFENSE_MECHANISM], position=self.grid_position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Create eventual children blocks and connections
        next_available_child_position = (self.grid_position[0] + 2*Node.Padding.X + Defense.width, self.grid_position[1])
        top_right_corner = self.get_top_right_corner()
        for child in self.children_attack_events:
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

    def __init__(self, data):
        super().__init__(data)
        self.loss_events : list[LossEvent] = []
    
    def compute_risk_tree_grid_coordinates(self):
        """
        Place every node in a grid. Every level is left-justified. The root is on top.
        Depth-first 'in-order' algorithm
        INPUT: position assigned to the current Node
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = (0,0)
        next_available_child_position = (self.grid_position[0], self.grid_position[1] + Actor.height + Node.Padding.Y)
        for child_node in self.loss_events:
            next_available_child_position = child_node.compute_risk_tree_grid_coordinates(next_available_child_position)
        next_spot_on_same_row = (next_available_child_position[0] + Node.Padding.X, self.grid_position[1])
        return next_spot_on_same_row

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass]):
        """In the context of a risk tree, create the setup representation for the node and add connections to its children"""
        # Create a block
        type = self.data[String.TYPE]
        
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ACTOR], position=self.grid_position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Link all related Loss events (abuse cases and attackers follow recursively) in a tree structure
        for loss_event in self.loss_events:
            loss_event.create_setup_class(setup_view, configuration_classes_gui)
            setup_view.create_connection_with_blocks(start_coordinate=loss_event.get_top_right_corner(), end_coordinate=self.get_top_left_corner())
    
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

    def __init__(self, data):
        super().__init__(data)
        self.attack_events : list[AttackEvent] = []
        self.abuse_cases : list[AbuseCase] = []
        self.actor : Actor
        
    def compute_risk_tree_grid_coordinates(self, position):
        """
        Place every node in a grid. Every level is left-justified. The root is on top.
        Depth-first 'in-order' algorithm
        INPUT: position assigned to the current Node
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position
        next_available_child_position = (self.grid_position[0], self.grid_position[1] + LossEvent.height + Node.Padding.Y)
        for child_node in self.abuse_cases:
            next_available_child_position = child_node.compute_risk_tree_grid_coordinates(next_available_child_position)
        next_spot_on_same_row = (next_available_child_position[0] + Node.Padding.X, self.grid_position[1])
        return next_spot_on_same_row
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass]):
        """In the contest of a risk tree, create the setup representation for the node and add connections to its children"""
        # Create a block
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.LOSS_EVENT], position=self.grid_position)
        
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Link all related Abuse cases (attackers follow recursively) in a tree structure
        for abuse_case in self.abuse_cases:
            abuse_case.create_setup_class(setup_view, configuration_classes_gui)
            setup_view.create_connection_with_blocks(start_coordinate=abuse_case.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

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

    def __init__(self, data):
        super().__init__(data)
        self.attacker : Attacker
        self.attack_events : list[AttackEvent] = [] # filled by YacrafModel.build()
        self.loss_events : list[LossEvent] = [] # filled by YacrafModel.build()

    def compute_risk_tree_grid_coordinates(self, position):
        """
        Place every node in a grid. Every level is left-justified. The root is on top.
        Depth-first 'in-order' algorithm
        INPUT: position assigned to the current Node
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position
        attacker_position = (self.grid_position[0], self.grid_position[1] + AbuseCase.height + Node.Padding.Y)
        self.attacker.compute_risk_tree_grid_coordinates(attacker_position)
        next_spot_on_same_row = (self.grid_position[0] + AbuseCase.width + Node.Padding.X, self.grid_position[1])
        return next_spot_on_same_row

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """In the context of a risk tree, create the setup representation for the node and add connections to its children"""
        # Create a block
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ABUSE_CASE], position=position)
        
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Link Attacker in a tree structure
        self.attacker.create_setup_class(setup_view, configuration_classes_gui)
        setup_view.create_connection_with_blocks(start_coordinate=self.attacker.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

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

    def __init__(self, data):
        super().__init__(data)
        self.abuse_cases : list[AbuseCase] = []

    def compute_risk_tree_grid_coordinates(self, position):
        """
        Place every node in a grid. Every level is left-justified. The root is on top.
        Depth-first 'in-order' algorithm
        INPUT: position assigned to the current Node
        OUTPUT: None
        """
        self.grid_position = position
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """In the context of a risk tree, create the setup representation for the node and add connections to its children"""
        # Create a block
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACKER], position=position)

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
