from abc import abstractmethod
from thesis_constants import *
from queue import SimpleQueue
from blocks_gui.setup.setup_class_gui import GUISetupClass
from views.setup_view import SetupView
from views.configuration_view import ConfigurationView
from blocks_gui.configuration.configuration_class_gui import GUIConfigurationClass
import copy
from model import Model
 
def set_default_attribute_values(type, setup_class_gui):
    attributes = setup_class_gui.get_setup_attributes_gui()
    match type:
        case String.AND | String.OR:
            attributes[Attack_event_setup_attribute.LOCAL_DIFFICULTY].set_entry_value("1/2/3") # TODO adapt to actual value
            return
        case String.DEFENSE:
            attributes[Defense_setup_attribute.COST].set_entry_value("10/20/30")
            attributes[Defense_setup_attribute.IMPACT].set_entry_value("20/30/40")

class YacrafModel():
    def __init__(self, defenses, abuse_cases, loss_events, attackers, actors):
        """Initialize the tree by positioning it on the screen and adding abuse cases and loss events"""
        self.__root: AttackEvent = None
        self.position = None
        self.defenses = [Defense(defense) for defense in defenses]
        self.abuse_cases = [AbuseCase(abuse_case) for abuse_case in abuse_cases]
        self.loss_events = [LossEvent(loss_event) for loss_event in loss_events]
        self.attackers = [Attacker(attacker) for attacker in attackers]
        self.actors = [Actor(actor) for actor in actors]

    def build(self, root_data, attack_events):
        """Build the YACRAF model by connecting all its components"""
        # Recursively build the attack graph, linking attack events and defense mechanisms
        self.__root = AttackEvent(root_data, attack_events=attack_events, defenses=self.defenses)
        
        for abuse_case in self.abuse_cases:
            # link the root and abuse case
            abuse_case.attack_events.append(self.__root)
            # link attacker and abuse case
            id = abuse_case.data[String.ATTACKER]
            for attacker in self.attackers:
                if str(attacker.data[String.ID]) == id:
                    abuse_case.attacker = attacker
                    attacker.abuse_cases.append(abuse_case)

        for loss_event in self.loss_events:
            # link the root and the loss events
            loss_event.attack_events.append(self.__root)
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
                        # We do not want to break. Check for validity of the model later instead.

        

    def compute_grid_coordinates(self, position):
        """Compute the grid coordinates for the tree elements"""
        # the root is at the position defined for the tree
        self.position = position
        self.__root.compute_children_grid_coordinates(self.position)

        # stack abuse_cases and loss_events above the root
        for i, abuse_case in enumerate(self.abuse_cases):
            abuse_case.grid_position = (self.position[0] - Units.ABUSE_CASE_WIDTH - 2*Units.HORIZONTAL_PADDING, self.position[1] - (i+1)*(Units.ABUSE_CASE_HEIGHT + Units.VERTICAL_PADDING))
        
        for i, loss_event in enumerate(self.loss_events):
            loss_event.grid_position = (self.position[0] + Units.LOSS_EVENT_WIDTH + 2*Units.HORIZONTAL_PADDING, self.position[1] - (i+1)*(Units.LOSS_EVENT_HEIGHT + Units.VERTICAL_PADDING))
        
        for i, defense in enumerate(self.defenses):
            # position for plotting in a separate setup view
            defense.grid_position = (i*(Units.DEFENSE_MECHANISM_WIDTH + 2 * Units.HORIZONTAL_PADDING + Units.ATTACK_EVENT_WIDTH), 0)

    def plot(self, model: Model):
        # TODO create setup_views on demand
        setup_view_attack_graph = model.get_setup_views()[0]
        setup_view_defenses = model.get_setup_views()[1]
        setup_view_risk = model.get_setup_views()[2]

        configuration_view_main : ConfigurationView = model.get_configuration_views()[Metamodel.YACRAF_1]
        configuration_classes_gui_main : list[GUIConfigurationClass]= configuration_view_main.get_configuration_classes_gui()
        
        ## create the node representations in the corresponding setup views
        self.__root.create_setup_class(setup_view_attack_graph, configuration_classes_gui_main)
        # stack abuse cases and loss event above the attack tree
        for abuse_case in self.abuse_cases:
            abuse_case.create_setup_class(setup_view_attack_graph, configuration_classes_gui_main)
        for loss_event in self.loss_events:
            loss_event.create_setup_class(setup_view_attack_graph, configuration_classes_gui_main)


        # plot defenses in another setup view
        start_position = (0, 0)
        for defense in self.defenses:
            defense.create_setup_class(setup_view_defenses, configuration_classes_gui_main, position=start_position, model=model)
            start_position = (start_position[0] + 2*Units.VERTICAL_PADDING + 2*Units.DEFENSE_MECHANISM_WIDTH, 0)
        
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

class Node():
    def __init__(self, data):
        self.data = data
        self.grid_position = None

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
    def __init__(self, data, attack_events=None, ancestors=None, defenses=None):
        """Recursively build the tree that has this Node as its root"""
        super().__init__(data)
        self.children_attack_events = []
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

    def compute_children_grid_coordinates(self, position):
        """
        Place every node in a grid. Every level is left-justified. The root is on top.
        Depth-first 'in-order' algorithm
        INPUT: position assigned to the current Node
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position
        if not self.children_attack_events:
            next_spot_on_same_row = (self.grid_position[0] + Units.ATTACK_EVENT_WIDTH + Units.HORIZONTAL_PADDING, self.grid_position[1])
            return next_spot_on_same_row
        child_node: AttackEvent
        child_position = (self.grid_position[0], self.grid_position[1] + Units.ATTACK_EVENT_HEIGHT + Units.VERTICAL_PADDING)
        for child_node in self.children_attack_events:
            child_position = child_node.compute_children_grid_coordinates(child_position)
        next_spot_on_same_row = (child_position[0] + Units.HORIZONTAL_PADDING, self.grid_position[1])
        return next_spot_on_same_row
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        type = self.data[String.TYPE]
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        
        self.setup_class_gui : GUISetupClass
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
            top_left_corner = (self.grid_position[0] - 1, self.grid_position[1] + 0.25)
            child_top_right_corner = (child.grid_position[0] + Units.ATTACK_EVENT_WIDTH, child.grid_position[1] + 0.25)
            setup_view.create_connection_with_blocks(start_coordinate=child_top_right_corner, end_coordinate=top_left_corner)
        

class Defense(Node):
    def __init__(self, data):
        super().__init__(data)
        
        # Attack steps add themselves to this list upon instantiation
        self.children_attack_events = []

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model : Model=None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.DEFENSE_MECHANISM], position=position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Create eventual children blocks and connections
        child : AttackEvent
        start_position = (position[0] + Units.VERTICAL_PADDING + Units.DEFENSE_MECHANISM_WIDTH, position[1])
        top_right_corner = (position[0] + Units.DEFENSE_MECHANISM_WIDTH, position[1] + 0.25)
        for child in self.children_attack_events:
            # stack the children
            linked_setup_class_gui = model.create_linked_setup_class_gui(child.setup_class_gui, setup_view, position=start_position)
            set_default_attribute_values(child.data[String.TYPE], linked_setup_class_gui)
            child_top_left_corner = (start_position[0] - 1, start_position[1] + 0.25)
            setup_view.create_connection_with_blocks(start_coordinate=top_right_corner, end_coordinate=child_top_left_corner)
            start_position = (start_position[0], start_position[1] + Units.SIMPLE_VERTICAL_PADDING + Units.ATTACK_EVENT_HEIGHT)


class AbuseCase(Node):
    def __init__(self, data):
        super().__init__(data)
        self.attacker : Attacker
        self.attack_events : list[AttackEvent] = [] # filled by YacrafModel.build()
        self.loss_events : list[LossEvent] = [] # filled by YacrafModel.build()

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ABUSE_CASE], position=position)
        
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Create eventual children blocks and connections
        top_right_corner = (self.grid_position[0] + Units.ABUSE_CASE_WIDTH, self.grid_position[1] + 0.25)
        root = self.attack_events[0]
        root_top_left_corner = (root.grid_position[0] - 1, root.grid_position[1] + 0.25)
        # connect to the root
        setup_view.create_connection_with_blocks(start_coordinate=top_right_corner, end_coordinate=root_top_left_corner)


class LossEvent(Node):
    def __init__(self, data):
        super().__init__(data)
        self.attack_events : list[AttackEvent] = []
        self.abuse_cases : list[AbuseCase] = []
        self.actor : Actor

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.LOSS_EVENT], position=position)
        
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # connect to the root
        root = self.attack_events[0]
        top_left_corner = (self.grid_position[0] - 1, self.grid_position[1] + 0.25)
        root_top_right_corner = (root.grid_position[0] + Units.ATTACK_EVENT_WIDTH, root.grid_position[1] + 0.25)
        
        setup_view.create_connection_with_blocks(start_coordinate=root_top_right_corner, end_coordinate=top_left_corner)
        

class Actor(Node):  
    def __init__(self, data):
        super().__init__(data)
        self.loss_events : list[LossEvent] = []
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        type = self.data[String.TYPE]
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ACTOR], position=position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Loss events connect to actors upon creation of setup class

class Attacker(Node):  
    def __init__(self, data):
        super().__init__(data)
        self.abuse_cases : list[AbuseCase] = []

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """create the setup representation for the node and add connections to its children"""
        # Create a block
        type = self.data[String.TYPE]
        position = self.grid_position if not position else position # use different position for plotting linked classes in another system_view
        
        self.setup_class_gui : GUISetupClass
        self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACKER], position=position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        set_default_attribute_values(type, self.setup_class_gui)

        # Create eventual children blocks and connections
        # TODO

class YacrafModelBuildError(Exception):
    """Raised when the defenses are added after the tree is built"""
    pass
