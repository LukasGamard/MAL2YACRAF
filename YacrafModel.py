from __future__ import annotations
import copy
import logging
from abc import abstractmethod
from pipeline_constants import *
from queue import SimpleQueue
from blocks_gui.setup.setup_class_gui import GUISetupClass
from views.setup_view import SetupView
from views.configuration_view import ConfigurationView
from blocks_gui.configuration.configuration_class_gui import GUIConfigurationClass
from typing import Any, Iterable, Iterator
from model import Model
 

class YacrafModel:
    def __init__(self, attack_tree_roots : list[AttackEvent],
                 attack_events : dict[int, AttackEvent],
                 defenses : dict[int, Defense],
                 abuse_cases : dict[int, AbuseCase],
                 loss_events : dict[int, LossEvent],
                 attackers : dict[int, Attacker],
                 actors : dict[int, Actor]):
        """
        Instantiate all elements in the YACRAF model
        Organize them in tree structures
        """
        self.attack_events = attack_events
        self.defenses = defenses
        self.abuse_cases = abuse_cases
        self.loss_events = loss_events
        self.attackers = attackers
        self.actors = actors
        # Recursively build the attack trees, adding children AttackEvents
        self.attack_trees = [root.build_attack_tree(self.attack_events) for root in attack_tree_roots]
        # Recursively build the risk trees, adding children to each layer
        self.risk_trees = [actor.build_risk_tree(loss_events, abuse_cases, attackers) for id, actor in self.actors.items()]
        # Build defense trees by linking the attack events to the defenses


    def plot(self, model: Model):
        logger = logging.getLogger(__name__) 
        # configuration classes defined in the yagraf model
        configuration_view : ConfigurationView = model.get_configuration_views()[Metamodel.YACRAF_1]
        configuration_classes_gui : list[GUIConfigurationClass]= configuration_view.get_configuration_classes_gui()
        
        ## Plot all attack trees
        # one view per tree
        # create setup_classes for AttackEvents
        logger.debug(f"Plotting {len(self.attack_trees)} attack trees")
        #setup_views_attack_tree : list[SetupView] = []
        for attack_tree in self.attack_trees:
            setup_view_attack_tree : SetupView = model.create_view(False, f"Attack Tree: {attack_tree.data[String.NAME]}")
            #setup_views_attack_tree.append(setup_view_attack_tree)
            attack_tree.create_setup_class(setup_view_attack_tree, configuration_classes_gui, (0, 0))
        
        ## Plot all defenses in the same view
        # create setup_classes for Defenses, linked_setup_classes for AttackEvents
        logger.debug(f"Plotting {len(self.defenses)} defenses")
        setup_view_defense : SetupView = model.create_view(False, f"Defense Mechanisms")
        position_offset = 0
        for id, defense in self.defenses.items():
            defense_position = (position_offset*(Defense.width + AttackEvent.width + 4*Node.Padding.X), 0)
            defense.create_setup_class(setup_view_defense, configuration_classes_gui, defense_position, model)
            position_offset += 1

        ## Plot the risk trees
        # one setup view per actor
        # create setup_classes for Actors, LossEvents, AbuseCases and Attackers
        logger.debug(f"Plotting {len(self.risk_trees)} risk trees")
        for actor in self.risk_trees:
            setup_view_risk = model.create_view(False, f"Risk for {actor.data[String.NAME]}")
            actor.create_setup_class(setup_view_risk, configuration_classes_gui, (0, 0))
        
        ## Link attack events to loss events
        # TODO: continue
        logger.debug("Linking attack events to loss events")
        for risk_tree in self.risk_trees:
            # one view per actor
            setup_view_attack_tree_top_level : SetupView = model.create_view(False, f"Abuse Cases/Loss Events for actor {risk_tree.data[String.NAME]}")            for loss_event in risk_tree:
                for loss_event in Actor.AbuseCaseIterator(risk_tree):
                    for abuse_case in loss_event.children:

        ## Plot the abuse cases and loss events linked to the top of an attack tree
        for attack_tree in self.attack_trees:
            for risk_tree in self.risk_trees:
                setup_view_attack_tree_top_level : SetupView = model.create_view(False, f"Abuse Cases/Loss Events for actor {risk_tree.data[String.NAME]}")
                start_position = (0, 0)

                # link the root of the attack tree
                linked_root : GUISetupClass = model.create_linked_setup_class_gui(attack_tree.setup_class_gui, setup_view_attack_tree_top_level, position=start_position)
                attack_tree.set_attribute_values(linked_root) # need to manually set the attribute values
                root_top_left_corner = Node.get_top_left_corner(start_position)
                root_top_right_corner = Node.get_top_right_corner(start_position)

                # Plot abuse cases
                seen_abuse_cases = set()
                for i, abuse_case in enumerate(Actor.AbuseCaseIterable(risk_tree)):
                    # only want unique abuse cases
                    if abuse_case.id in seen_abuse_cases:
                        logger.debug(f"Skipping already seen abuse case {abuse_case.data[String.NAME]} for actor {risk_tree.data[String.NAME]}")
                        continue
                    seen_abuse_cases.add(abuse_case.id)

                    logger.debug(f"Copying abuse case {abuse_case.data[String.NAME]} for actor {risk_tree.data[String.NAME]}")
                    abuse_case_position = (start_position[0] - AbuseCase.width - 2*Node.Padding.X, start_position[1] + i*(AbuseCase.height + Node.Padding.Y))
                    linked_abuse_case : GUISetupClass = model.create_linked_setup_class_gui(abuse_case.setup_class_gui, setup_view_attack_tree_top_level, position=abuse_case_position)
                    abuse_case.set_attribute_values(linked_abuse_case)
                    abuse_case_top_right_corner = Node.get_top_right_corner(abuse_case_position)
                    setup_view_attack_tree_top_level.create_connection_with_blocks(start_coordinate=abuse_case_top_right_corner, end_coordinate=root_top_left_corner)
                
                # Plot the loss events
                for i, loss_event in enumerate(Actor.LossEventIterable(risk_tree)):
                    logger.debug(f"Copying loss event {loss_event.data[String.NAME]} for actor {risk_tree.data[String.NAME]}")
                    loss_event_position = (start_position[0] + AttackEvent.width + 2*Node.Padding.X, start_position[1] + i*(LossEvent.height + Node.Padding.Y))
                    linked_loss_event : GUISetupClass = model.create_linked_setup_class_gui(loss_event.setup_class_gui, setup_view_attack_tree_top_level, position=loss_event_position)
                    loss_event.set_attribute_values(linked_loss_event)
                    loss_event_top_left_corner = Node.get_top_left_corner(loss_event_position)
                    setup_view_attack_tree_top_level.create_connection_with_blocks(start_coordinate=root_top_right_corner, end_coordinate=loss_event_top_left_corner)
        

class Node:
    """Base class for all nodes in the YACRAF model"""
    class Offset:
        """Offsets used for the connecting nodes"""
        X = 0.95
        Y = 0.25

    class Padding:
        """Padding used for the connecting nodes"""
        X = 2
        Y = 4

    width = 11
    height = 1

    def __init__(self, data):
        self.data : dict[str, Any] = data
        self.id : int = data[String.ID]
        #self.children : list[Node]
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


class AttackEvent(Node):
    """
    Class representing an attack event in the YACRAF model.
    Iterable on a subtree basis.
    """

    height = 5

    def __init__(self, data)#, attack_events, ancestors=None):
        """Recursively build the tree that has this Node as its root"""
        super().__init__(data)
        self.children : list[AttackEvent]= []
        self.ancestors : list[int] = []#ancestors
        self.defenses : list[Defense] = []
        self.loss_events : list[LossEvent] = []
        self.abuse_case : AbuseCase

        #if self.data[String.CHILDREN]:
         #   self.__add_children_nodes(attack_events)
    
    def build_attack_tree(self, attack_events : dict[int, AttackEvent], ancestors=None) -> AttackEvent:
        """recursive bottom-up process to pull and connect children attack_events"""
        # base case: no children
        for id, name in self.data[String.CHILDREN].items():
            if self.ancestors and int(id) in self.ancestors:
                # avoid loops
                return
            ancestors : list = copy.deepcopy(self.ancestors) if self.ancestors else []
            ancestors.append(int(self.data[String.ID]))
            self.children.append(attack_events[int(id)].build_attack_tree(attack_events, ancestors=ancestors))

        return self
    
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
                self.set_attribute_values()
                self.setup_class_gui.set_name(self.data[String.NAME])
                self.setup_class_gui.update_text()

                next_spot_on_same_row = (position[0] + AttackEvent.width + Node.Padding.X, position[1])
                return next_spot_on_same_row
            
            # Plot children
            next_available_child_position = (position[0], position[1] + AttackEvent.height + Node.Padding.Y)
            for child in self.children:   
                next_available_child_position = child.create_setup_class(setup_view, configuration_classes_gui, position=next_available_child_position)              

        # Create a visual block representation
        type = self.data[String.TYPE]
        if type == String.AND:
            self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_AND], position=position)
        elif type == String.OR:
            self.setup_class_gui = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACK_EVENT_OR], position=position)
        # Initialize its attribute values
        self.set_attribute_values()
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()

        # Connect children to the parent
        for child in self.children:
            setup_view.create_connection_with_blocks(start_coordinate=child.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

        if full_attack_tree:
            next_spot_on_same_row = (next_available_child_position[0] + 2*Node.Padding.X, position[1])
        else:
            next_spot_on_same_row = (position[0] + Node.Padding.X, position[1])
        return next_spot_on_same_row

    def set_attribute_values(self, setup_class_gui=None):
        """
        Set the attribute values for the setup class.
        If setup_class_gui is None, initialize attribute values for the setup_class_gui of the current instance.
        Use the attribute values from the current instance.
        """
        attributes = self.setup_class_gui.get_setup_attributes_gui() if setup_class_gui is None else setup_class_gui.get_setup_attributes_gui()
        attributes[Attack_event_setup_attribute.TYPE].set_entry_value(self.data[String.TYPE])
        if String.LOCAL_DIFFICULTY in self.data and self.data[String.LOCAL_DIFFICULTY]:
            attributes[Attack_event_setup_attribute.LOCAL_DIFFICULTY].set_entry_value(self.data[String.LOCAL_DIFFICULTY])
        else:
            attributes[Attack_event_setup_attribute.LOCAL_DIFFICULTY].set_entry_value("1/5/10")

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

    def __init__(self, defense_data)#, attack_trees : list[AttackEvent]):
        super().__init__(defense_data)
        
        # Attack steps add themselves to this list upon instantiation
        self.attack_events : list[AttackEvent] = []
        #for tree in attack_trees:
         #   for attack_event in tree:
          #      if str(attack_event.data[String.ID]) in self.data[String.CHILDREN]:
           #         self.attack_events.append(attack_event)

    def build_defense_tree(self, attack_events : dict[int, AttackEvent]) -> Defense:
        """
        Build the defense tree by adding children AttackEvents.
        This is a bottom-up process, starting from the leaf nodes.
        """
        # base case: no children
        for id, name in self.data[String.CHILDREN].items():
            if int(id) in attack_events:
                # add the attack event to the defense
                self.attack_events.append(attack_events[int(id)])
        
        return self
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position, model : Model):
        """create the setup representation for the node and add connections to its children"""
        logger = logging.getLogger(__name__)
        self.grid_position = position

        # Create a block
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.DEFENSE_MECHANISM], position=self.grid_position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        self.set_attribute_values()

        # Create eventual children blocks and connections
        next_available_child_position = (self.grid_position[0] + 2*Node.Padding.X + Defense.width, self.grid_position[1])
        top_right_corner = self.get_top_right_corner()
        for child in self.children:
            # stack the children
            linked_setup_class_gui = model.create_linked_setup_class_gui(child.setup_class_gui, setup_view, position=next_available_child_position)
            # set the attribute values for the linked setup class
            # manually copy from the original setup class
            logger.debug(f"Copying setup class {child.setup_class_gui.get_name()} for attack event {child.data[String.NAME]} for defense {self.data[String.NAME]}")
            child.set_attribute_values(linked_setup_class_gui)
            child_top_left_corner = Node.get_top_left_corner(next_available_child_position)
            setup_view.create_connection_with_blocks(start_coordinate=top_right_corner, end_coordinate=child_top_left_corner)
            next_available_child_position = (next_available_child_position[0], next_available_child_position[1] + Node.Padding.X + AttackEvent.height)

    def set_attribute_values(self, setup_class_gui=None):
        """
        Set the attribute values for the setup class.
        If setup_class_gui is None, initialize attribute values for the setup_class_gui of the current instance.
        Use the attribute values from the current instance.
        """
        attributes = self.setup_class_gui.get_setup_attributes_gui() if setup_class_gui is None else setup_class_gui.get_setup_attributes_gui()
        attributes[Defense_setup_attribute.COST].set_entry_value(self.data[String.COST])
        attributes[Defense_setup_attribute.IMPACT].set_entry_value(self.data[String.IMPACT])

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
            for loss_event in self.actor_instance.loss_events:
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
            for loss_event in self.actor_instance.loss_events:
                self.fifo.put(loss_event)

        def __iter__(self) -> Iterator[LossEvent]:
            return self

        def __next__(self):
            if not self.fifo.empty():
                return self.fifo.get()
            else:
                raise StopIteration

    def __init__(self, actor_data)#, loss_events_data, abuse_cases_data, attackers_data):
        super().__init__(actor_data)
        self.loss_events : list[LossEvent] = []#[LossEvent(loss_events_data[id], abuse_cases_data, attackers_data) for id in actor_data[String.LOSS_EVENTS].keys()]

    def build_risk_tree(self,
                        loss_events : dict[int, LossEvent],
                        abuse_cases : dict[int, AbuseCase],
                        attackers : dict [int, Attacker]) -> Actor:
        """
        Build the risk tree for the actor by adding loss events, abuse cases and attackers
        """
        for id, loss_event in self.data[String.LOSS_EVENTS].items():
            if int(id) in loss_events:
                # add the loss event to the actor
                loss_event_instance = loss_events[int(id)]
                self.loss_events.append(loss_event_instance)
                # add the abuse cases and attackers to the loss event
                for abuse_case_id in loss_event.data[String.ABUSE_CASES]:
                    if int(abuse_case_id) in abuse_cases:
                        abuse_case_instance = abuse_cases[int(abuse_case_id)]
                        loss_event_instance.abuse_cases.append(abuse_case_instance)
                        # add the attacker to the abuse case
                        attacker_dict = abuse_case_instance.data[String.ATTACKER]
                        abuse_case_instance_attacker_id = int(next(iter(attacker_dict.keys())))
                        if abuse_case_instance_attacker_id in attackers:
                            abuse_case_instance.attacker = attackers[abuse_case_instance_attacker_id]
 
        return self
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position):
        """
        In the context of a risk tree, create the setup representation for the node and add connections to its children
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position

        # Build the risk tree "inorder", from the bottom up
        # Plot loss_events
        next_available_child_position = (position[0], position[1] + Actor.height + Node.Padding.Y)
        for loss_events in self.loss_events:   
            next_available_child_position = loss_events.create_setup_class(setup_view, configuration_classes_gui, next_available_child_position)              
        
        # Create a visual block representation
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ACTOR], position=position)

        # Initialize attribute values 
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        self.set_attribute_values()

        # Connect children to the parent
        for loss_events in self.loss_events:
            setup_view.create_connection_with_blocks(start_coordinate=loss_events.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

        next_spot_on_same_row = (next_available_child_position[0] + 2*Node.Padding.X, position[1])
        return next_spot_on_same_row

    def set_attribute_values(self, setup_class_gui=None):
        """
        Set the attribute values for the setup class.
        If setup_class_gui is None, initialize attribute values for the setup_class_gui of the current instance.
        Use the attribute values from the current instance.
        """
        attributes = self.setup_class_gui.get_setup_attributes_gui() if setup_class_gui is None else setup_class_gui.get_setup_attributes_gui()
        attributes[Actor_setup_attribute.TYPE].set_entry_value(self.data[String.TYPE])

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

    def __init__(self, loss_event_data)#, abuse_cases_data, attackers_data):
        super().__init__(loss_event_data)
        self.abuse_cases : list[AbuseCase] = []#[AbuseCase(abuse_cases_data[id], attackers_data) for id in loss_event_data[String.ABUSE_CASES].keys()]
        self.attack_events : list[AttackEvent] = []
        self.actor : Actor
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position):
        """In the contest of a risk tree, create the setup representation for the node and add connections to its children"""
        self.grid_position = position

        # Plot the abuse_cases
        next_available_child_position = (position[0], position[1] + LossEvent.height + Node.Padding.Y)
        for abuse_case in self.abuse_cases:
            next_available_child_position = abuse_case.create_setup_class(setup_view, configuration_classes_gui, next_available_child_position)
        
        # Create a block
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.LOSS_EVENT], position=self.grid_position)
        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        self.set_attribute_values()

        # Connect abuse_cases to the parent
        for abuse_case in self.abuse_cases:
            setup_view.create_connection_with_blocks(start_coordinate=abuse_case.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

        next_spot_on_same_row = (next_available_child_position[0] + 2*Node.Padding.X, position[1])
        return next_spot_on_same_row
    
    def set_attribute_values(self, setup_class_gui=None):
        """
        Set the attribute values for the setup class.
        If setup_class_gui is None, initialize attribute values for the setup_class_gui of the current instance.
        Use the attribute values from the current instance.
        """
        attributes = self.setup_class_gui.get_setup_attributes_gui() if setup_class_gui is None else setup_class_gui.get_setup_attributes_gui()
        attributes[Loss_event_setup_attribute.TYPE].set_entry_value(self.data[String.TYPE])
        attributes[Loss_event_setup_attribute.MAGNITUDE].set_entry_value(self.data[String.MAGNITUDE])

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

    def __init__(self, abuse_case_data)#, attackers_data):
        super().__init__(abuse_case_data)
        #attacker_dict = abuse_case_data[String.ATTACKER]
        #attacker_name = attacker_dict[next(iter(attacker_dict.keys()))]
        # NOTE: unhandy code because of the json format trying to be consistent with the previous format
        self.attacker : Attacker#= Attacker(attackers_data[attacker_name])
        self.loss_events : list[LossEvent] = []
        self.attack_events : list[AttackEvent] = []

    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position):
        """
        In the context of a risk tree, create the setup representation for the node and add connections to its children
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position

        # Plot the child
        next_available_child_position = (position[0], position[1] + AbuseCase.height + Node.Padding.Y)
        self.attacker.create_setup_class(setup_view, configuration_classes_gui, position=next_available_child_position)

        # Plot a block
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ABUSE_CASE], position=position)

        # connect the child to the parent
        setup_view.create_connection_with_blocks(start_coordinate=self.attacker.get_top_right_corner(), end_coordinate=self.get_top_left_corner())

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.set_attribute_values()
        self.setup_class_gui.update_text()

        # Link Attacker in a tree structure
        #attacker_position = (self.grid_position[0], self.grid_position[1] + AbuseCase.height + Node.Padding.Y)
        #self.child.create_setup_class(setup_view, configuration_classes_gui, attacker_position)
        #setup_view.create_connection_with_blocks(start_coordinate=self.child.get_top_right_corner(), end_coordinate=self.get_top_left_corner())
        next_spot_on_same_row = (self.grid_position[0] + AbuseCase.width + 2*Node.Padding.X, self.grid_position[1])
        return next_spot_on_same_row

    def set_attribute_values(self, setup_class_gui=None):
        """
        Set the attribute values for the setup class.
        If setup_class_gui is None, initialize attribute values for the setup_class_gui of the current instance.
        Use the attribute values from the current instance.
        """
        attributes = self.setup_class_gui.get_setup_attributes_gui() if setup_class_gui is None else setup_class_gui.get_setup_attributes_gui()
        att = attributes[Abuse_case_setup_attribute.ACCESSIBILITY_TO_ATTACK_SURFACE]
        #attributes[Abuse_case_setup_attribute.ACCESSIBILITY_TO_ATTACK_SURFACE].set_entry_value(self.data[String.ACCESSIBILITY_TO_ATTACK_SURFACE])
        attributes[Abuse_case_setup_attribute.WINDOW_OF_OPPORTUNITY].set_entry_value(self.data[String.WINDOW_OF_OPPORTUNITY])
        attributes[Abuse_case_setup_attribute.ABILITY_TO_REPUDIATE].set_entry_value(self.data[String.ABILITY_TO_REPUDIATE])
        attributes[Abuse_case_setup_attribute.PERCEIVED_DETERRENCE].set_entry_value(self.data[String.PERCEIVED_DETERRENCE])
        attributes[Abuse_case_setup_attribute.PERCEIVED_EASE_OF_ATTACK].set_entry_value(self.data[String.PERCEIVED_EASE_OF_ATTACK])
        attributes[Abuse_case_setup_attribute.PERCEIVED_BENEFIT_OF_SUCCESS].set_entry_value(self.data[String.PERCEIVED_BENEFIT_OF_SUCCESS])
        attributes[Abuse_case_setup_attribute.EFFORT_SPENT].set_entry_value(self.data[String.EFFORT_SPENT])

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
        self.abuse_cases : list[AbuseCase] = []
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position):
        """In the context of a risk tree, create the setup representation for the node and add connections to its children"""
        # Create a block
        self.grid_position = position
        
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.ATTACKER], position=position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        self.set_attribute_values()

    def set_attribute_values(self, setup_class_gui=None):
        """
        Set the attribute values for the setup class.
        If setup_class_gui is None, initialize attribute values for the setup_class_gui of the current instance.
        Use the attribute values from the current instance.
        """
        attributes = self.setup_class_gui.get_setup_attributes_gui() if setup_class_gui is None else setup_class_gui.get_setup_attributes_gui()
        attributes[Attacker_setup_attribute.PERSONAL_RISK_TOLERANCE].set_entry_value(self.data[String.PERSONAL_RISK_TOLERANCE])
        attributes[Attacker_setup_attribute.CONCERN_FOR_COLLATERAL_DAMAGE].set_entry_value(self.data[String.CONCERN_FOR_COLLATERAL_DAMAGE])
        attributes[Attacker_setup_attribute.SKILL].set_entry_value(self.data[String.SKILL])
        attributes[Attacker_setup_attribute.RESOURCES].set_entry_value(self.data[String.RESOURCES])
        attributes[Attacker_setup_attribute.SPONSORSHIP].set_entry_value(self.data[String.SPONSORSHIP])

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
