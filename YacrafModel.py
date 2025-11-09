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

logger = logging.getLogger(__name__)
 

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
        logger = logging.getLogger(__name__)


        ## Recursively build the attack trees, adding children AttackEvents
        # Build as a tree to shortcut loops in the attack graph
        self.attack_trees = [root.build_attack_tree(self.attack_events) for root in attack_tree_roots]
        logger.debug(f"Built {len(self.attack_trees)} attack trees")
        logger.debug(f"Attack trees details:{self.attack_trees}")
        for attack_tree in self.attack_trees:
            pass#logger.debug(f"Attack tree rooted at attack event id:{attack_tree.data[String.ID]}")

        
        ## Connect the remaining elements in the model
        # Attack_events get connected through defenses, abuse_cases and loss_events
        self.defenses = {id: defense.connect(self.attack_events) for id, defense in self.defenses.items()}
        self.actors = {id: actor.connect(self.loss_events) for id, actor in self.actors.items()}
        self.loss_events = {id: loss_event.connect(self.abuse_cases, self.attack_events) for id, loss_event in self.loss_events.items()}
        self.abuse_cases = {id: abuse_case.connect(self.attackers, attack_events) for id, abuse_case in self.abuse_cases.items()}

    def isValid(self) -> bool:
        """
        Check if the model is valid.
        A model is valid if it has a single attacker and respects the multiplicities in the YACRAF metamodel.
        """
        valid_attack_events = all(attack_event.isValid() for attack_event in self.attack_events.values())
        valid_defense = all(defense.isValid() for defense in self.defenses.values())
        valid_abuse_cases = all(abuse_case.isValid() for abuse_case in self.abuse_cases.values())
        valid_loss_events = all(loss_event.isValid() for loss_event in self.loss_events.values())
        valid_attacker = len(self.attackers) == 1 and all(attacker.isValid() for attacker in self.attackers.values())
        valid_actors = all(actor.isValid() for actor in self.actors.values())
        return (valid_attacker and valid_attack_events and valid_defense and
                valid_abuse_cases and valid_loss_events and valid_actors)
    

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
            logger.debug(f"Plotting attack tree rooted at attack event id:{attack_tree.id}")
            logger.debug(f'Roots children: {attack_tree.children}')
            setup_view_attack_tree : SetupView = model.create_view(False, f"Attack Tree: {attack_tree.data[String.NAME]}")
            attack_tree.create_setup_class(setup_view_attack_tree, configuration_classes_gui, (0, 0))
        
        ## Plot all defenses in the same view
        # create setup_classes for Defenses, linked_setup_classes for AttackEvents
        logger.debug(f"Plotting {len(self.defenses)} defenses")
        setup_view_defense : SetupView = model.create_view(False, f"Defense Mechanisms")
        position_offset = 0
        for defense in self.defenses.values():
            defense_position = (position_offset*(Defense.width + AttackEvent.width + 4*Node.Padding.X), 0)
            defense.create_setup_class(setup_view_defense, configuration_classes_gui, defense_position, model)
            position_offset += 1

        ## Plot the risk trees
        # one setup view per actor
        # create setup_classes for Actors, LossEvents, AbuseCases and Attackers
        logger.debug(f"Plotting {len(self.actors)} risk trees")
        for actor in self.actors.values():
            setup_view_risk = model.create_view(False, f"Risk for {actor.data[String.NAME]}")
            actor.create_setup_class(setup_view_risk, configuration_classes_gui, (0, 0))
        
        ## Link attack events to loss events
        logger.debug("Linking loss events to attacke events and abuse cases")

        already_linked_loss_events : dict[int, LossEvent]= {}  # to avoid linking the same loss event multiple times
        already_linked_attack_events : dict[int, AttackEvent] = {}  # to avoid linking the same attack event multiple times
        for actor in self.actors.values():
            # one view per actor
            setup_view_attack_tree_top_level : SetupView = model.create_view(False, f"Abuse Cases/Loss Events for actor {actor.data[String.NAME]}")            
            # Calulator allows to fan out **after** the LossEvent level
            loss_event_position = (3* LossEvent.width + 4*Node.Padding.X, 0)

            for loss_event in Actor.LossEventIterator(actor):
                if loss_event.id in already_linked_loss_events:
                    # this loss event has already been linked to an attack event
                    linked_loss_event : GUISetupClass = model.create_linked_setup_class_gui(already_linked_loss_events[loss_event.id].setup_class_gui, setup_view_attack_tree_top_level, position=loss_event_position)
                    already_linked_loss_events[loss_event.id].set_attribute_values(linked_loss_event)
                    # Nothing to connect here
                    loss_event_position = (loss_event_position[0], loss_event_position[1] + LossEvent.height + Node.Padding.Y)
                    continue

                for attack_event in loss_event.attack_events:
                    # Copy the loss_event from the risk tree
                    linked_loss_event : GUISetupClass = model.create_linked_setup_class_gui(loss_event.setup_class_gui, setup_view_attack_tree_top_level, position=loss_event_position)
                    loss_event.set_attribute_values(linked_loss_event) # copy values over
                    loss_event_top_left_corner = Node.get_top_left_corner(loss_event_position)

                    attack_event_position = (loss_event_position[0] - AttackEvent.width - 2*Node.Padding.X, loss_event_position[1])

                    # Link the attack event to the loss event
                    if attack_event.id in already_linked_attack_events:
                        # this attack event has already been linked to a loss event
                        linked_attack_event : GUISetupClass = model.create_linked_setup_class_gui(already_linked_attack_events[attack_event.id].setup_class_gui, setup_view_attack_tree_top_level, position=attack_event_position)
                        already_linked_attack_events[attack_event.id].set_attribute_values(linked_attack_event)
                        # Connect to loss_event
                        attack_event_top_right_corner = Node.get_top_right_corner(attack_event_position)
                        setup_view_attack_tree_top_level.create_connection_with_blocks(start_coordinate=attack_event_top_right_corner, end_coordinate=loss_event_top_left_corner)

                        loss_event_position = (loss_event_position[0], loss_event_position[1] + AttackEvent.height + Node.Padding.Y)
                        continue

                    linked_attack_event : GUISetupClass = model.create_linked_setup_class_gui(attack_event.setup_class_gui, setup_view_attack_tree_top_level, position=attack_event_position)
                    attack_event.set_attribute_values(linked_attack_event)
                    # Create a connection from the attack event to the loss event
                    attack_event_top_right_corner = Node.get_top_right_corner(attack_event_position)
                    setup_view_attack_tree_top_level.create_connection_with_blocks(start_coordinate=attack_event_top_right_corner, end_coordinate=loss_event_top_left_corner)

                    # Link the attack event to its abuse case
                    abuse_case_position = (attack_event_position[0] - AbuseCase.width - 2*Node.Padding.X, attack_event_position[1])
                    linked_abuse_case : GUISetupClass = model.create_linked_setup_class_gui(attack_event.abuse_case.setup_class_gui, setup_view_attack_tree_top_level, position=abuse_case_position)
                    attack_event.abuse_case.set_attribute_values(linked_abuse_case)
                    linked_abuse_case_top_right_corner = Node.get_top_right_corner(abuse_case_position)
                    attack_event_top_left_corner = Node.get_top_left_corner(attack_event_position)
                    # Create a connection from the abuse case to the attack event
                    setup_view_attack_tree_top_level.create_connection_with_blocks(start_coordinate=linked_abuse_case_top_right_corner, end_coordinate=attack_event_top_left_corner)
                    
                    loss_event_position = (loss_event_position[0], loss_event_position[1] + AbuseCase.height + Node.Padding.Y)

                    already_linked_attack_events[attack_event.id] = attack_event
                already_linked_loss_events[loss_event.id] = loss_event

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
        self.setup_class_gui : GUISetupClass
        self.grid_position : tuple[float, float]
        #logger.debug(f"Created node id:{self.id} name:{self.data[String.NAME]}")
        #logger.debug(f"Data: {data}")

    def __repr__(self):
        return f"{self.__class__.__name__}:{self.data[String.NAME]}:{self.data[String.ID]}"
    
    def __str__(self):
        return f"id:{self.data[String.ID]}"

    @abstractmethod
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position = None, model=None):
        """create the setup representation for the node and add connections to its children"""
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

    def __init__(self, data):
        """Recursively build the tree that has this Node as its root"""
        super().__init__(data)
        self.children : list[AttackEvent]= []
        self.ancestors : list[int] = []
        self.defenses : list[Defense] = []
        self.loss_events : list[LossEvent] = []
        self.abuse_case : AbuseCase = None
    
    def isValid(self) -> bool:
        """
        Check if the attack event is valid.
        An attack event is valid if it respects YACRAF multiplicities.
        """
        return True
        # The composition requirement doesn't induce a multiplicity constraint
        if len(self.ancestors) > 0:
            return True
        
        # Only the root of the attack tree has a corresponding abuse case
        is_valid = self.abuse_case is not None
        if not is_valid:
            logger = logging.getLogger(__name__)
            logger.warning(f"Attack event id:{self.data[String.ID]} is not valid: it is a root of an attack tree but has no abuse case.")
        return is_valid

    def build_attack_tree(self, attack_events : dict[int, AttackEvent], ancestors=None) -> AttackEvent:
        """recursive bottom-up process to pull and connect children attack_events"""
        logger = logging.getLogger(__name__)
        #logger.debug(f"Building attack tree for attack event id:{self.data[String.ID]}")
        #logger.debug(f"Current ancestors: {ancestors}")
        #logger.debug(f"Current children: {self.data[String.CHILDREN]}")
        self.ancestors : list = copy.deepcopy(ancestors) if ancestors else []
        logger.debug(f"Processing children: {self.data[String.CHILDREN]} for parent id:{self.data[String.ID]}")
        for id, name in self.data[String.CHILDREN].items():
            logger.debug(f"Processing child id:{id} name:{name} for parent id:{self.data[String.ID]}")
            if self.ancestors and int(id) in self.ancestors:
                # avoid loops
                return
            self.ancestors.append(int(self.data[String.ID]))
            self.children.append(attack_events[int(id)].build_attack_tree(attack_events, ancestors=self.ancestors))

        logger.debug(f"Built attack tree for attack event id:{self.id} with children {self.children}")
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
        Recursively create the setup representation for the node and add connections to its children        
        OUTPUT: next available position for the sub-tree on the same level
        """
        self.grid_position = position
        logger = logging.getLogger(__name__)

        # Recursively build the tree "inorder", from the bottom up
        if full_attack_tree:
            logger.debug(f"Children: {self.children} of parent {self.id}")
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
                logger.debug(f"Plotting child {child} of parent {self.data[String.NAME]}")
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
            attributes[Attack_event_setup_attribute.LOCAL_DIFFICULTY].set_entry_value("2/5/8") # Eyeballed normal distribution

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

    def __init__(self, defense_data):
        super().__init__(defense_data)
        self.attack_events : list[AttackEvent] = []

    def connect(self, attack_events : dict[int, AttackEvent]) -> Defense:
        """
        Build the defense tree by adding children AttackEvents.
        This is a bottom-up process, starting from the leaf nodes.
        """
        for id, name in self.data[String.CHILDREN].items():
            if int(id) in attack_events:
                # add the attack event to the defense and vice-versa
                self.attack_events.append(attack_events[int(id)])
                attack_events[int(id)].defenses.append(self)
        return self
    
    def isValid(self) -> bool:
        """
        Check if the defense is valid.
        A defense is valid if it respects YACRAF multiplicities.
        """
        return True
    
    def create_setup_class(self, setup_view : SetupView, configuration_classes_gui : list[GUIConfigurationClass], position, model : Model):
        """create the setup representation for the node and add connections to its children"""
        logger = logging.getLogger(__name__)
        self.grid_position = position

        # Create a block
        self.setup_class_gui : GUISetupClass = setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[Configuration_classes_gui.DEFENSE_MECHANISM], position=self.grid_position)

        self.setup_class_gui.set_name(self.data[String.NAME])
        self.setup_class_gui.update_text()
        self.set_attribute_values()

        # Create children
        next_available_attack_event_position = (self.grid_position[0] + 2*Node.Padding.X + Defense.width, self.grid_position[1])
        top_right_corner = self.get_top_right_corner()
        for attack_event in self.attack_events:
            # stack the attack_events
            linked_setup_class_gui = model.create_linked_setup_class_gui(attack_event.setup_class_gui, setup_view, position=next_available_attack_event_position)
            # set the attribute values for the linked setup class
            # manually copy from the original setup class
            logger.debug(f"Copying setup class {attack_event.setup_class_gui.get_name()} for attack event {attack_event.data[String.NAME]} for defense {self.data[String.NAME]}")
            attack_event.set_attribute_values(linked_setup_class_gui)
            attack_event_top_left_corner = Node.get_top_left_corner(next_available_attack_event_position)
            setup_view.create_connection_with_blocks(start_coordinate=top_right_corner, end_coordinate=attack_event_top_left_corner)
            next_available_attack_event_position = (next_available_attack_event_position[0], next_available_attack_event_position[1] + Node.Padding.X + AttackEvent.height)

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

    def __init__(self, actor_data):
        super().__init__(actor_data)
        self.loss_events : list[LossEvent] = []

    def isValid(self) -> bool:
        """
        Check if the actor is valid.
        An actor is valid if it respects YACRAF multiplicities.
        """
        return True
    
    def connect(self, loss_events : dict[int, LossEvent]) -> Actor:
        """
        Build the actor tree by adding children LossEvents.
        This is a bottom-up process, starting from the leaf nodes.
        """
        for id, name in self.data[String.LOSS_EVENTS].items():
            if int(id) in loss_events:
                # add the loss event to the actor and vice-versa
                self.loss_events.append(loss_events[int(id)])
                loss_events[int(id)].actor = self
        
        return self
    
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
                for abuse_case_id in loss_event_instance.data[String.ABUSE_CASES]:
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

    def __init__(self, loss_event_data):
        super().__init__(loss_event_data)
        self.abuse_cases : list[AbuseCase] = []
        self.attack_events : list[AttackEvent] = []
        self.actor : Actor = None
    
    def isValid(self) -> bool:
        """
        Check if the loss event is valid.
        A loss event is valid if it respects YACRAF multiplicities.
        """
        is_valid = len(self.abuse_cases) > 0 and len(self.attack_events) > 0 and self.actor is not None
        if not is_valid:
            logger = logging.getLogger(__name__)
            logger.warning(f"Loss event id:{self.data[String.ID]} is not valid: #abuse_cases={len(self.abuse_cases)}, #attack_events={len(self.attack_events)}, actor={self.actor}")
        return is_valid
    
    def connect(self, abuse_cases : dict[int, AbuseCase], attack_events : dict[int, AttackEvent]) -> LossEvent:
        """
        Build the loss event tree by adding children AbuseCases and AttackEvents.
        This is a bottom-up process, starting from the leaf nodes.
        """
        for id, name in self.data[String.ABUSE_CASES].items():
            if int(id) in abuse_cases:
                # add the abuse case to the loss event and vice-versa
                self.abuse_cases.append(abuse_cases[int(id)])
                abuse_cases[int(id)].loss_events.append(self)
        
        for id, name in self.data[String.ATTACK_STEPS].items():
            if int(id) in attack_events:
                # add the attack event to the loss event and vice-versa
                self.attack_events.append(attack_events[int(id)])
                attack_events[int(id)].loss_events.append(self)

        return self
    
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

    def __init__(self, abuse_case_data):
        super().__init__(abuse_case_data)
        self.attacker : Attacker
        self.loss_events : list[LossEvent] = []
        self.attack_events : list[AttackEvent] = []

    def isValid(self) -> bool:
        """
        Check if the abuse case is valid.
        An abuse case is valid if it respects YACRAF multiplicities.
        """
        is_valid = self.attacker is not None and len(self.loss_events) > 0 and len(self.attack_events) > 0
        if not is_valid:
            logger = logging.getLogger(__name__)
            logger.warning(f"Abuse case id:{self.data[String.ID]} is not valid: attacker={self.attacker}, #loss_events={len(self.loss_events)}, #attack_events={len(self.attack_events)}")
        return is_valid
    
    def connect(self, attackers : dict[int, Attacker], attack_events : dict[int, AttackEvent]) -> AbuseCase:
        """
        Build the abuse case tree by adding an attacker.
        This is a bottom-up process, starting from the leaf nodes.
        """
        # Connect attacker
        # NOTE: the attacker is a dictionary with a single key, so we can just take the first one
        attacker_dict = self.data[String.ATTACKER]
        attacker_id = int(next(iter(attacker_dict.keys())))
        if attacker_id in attackers:
            # add the attacker to the abuse case and vice-versa
            self.attacker = attackers[attacker_id]
            self.attacker.abuse_cases.append(self)
        
        # Connect attack_events
        for id, name in self.data[String.ATTACK_STEPS].items():
            if int(id) in attack_events:
                # add the attack event to the abuse case and vice-versa
                self.attack_events.append(attack_events[int(id)])
                attack_events[int(id)].abuse_case = self

        # loss_events already connected to the abuse case in LossEvent.connect()
        return self
    
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
        next_spot_on_same_row = (self.grid_position[0] + AbuseCase.width + 2*Node.Padding.X, self.grid_position[1])
        return next_spot_on_same_row

    def set_attribute_values(self, setup_class_gui=None):
        """
        Set the attribute values for the setup class.
        If setup_class_gui is None, initialize attribute values for the setup_class_gui of the current instance.
        Use the attribute values from the current instance.
        """
        attributes = self.setup_class_gui.get_setup_attributes_gui() if setup_class_gui is None else setup_class_gui.get_setup_attributes_gui()
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
    
    def isValid(self) -> bool:
        """
        Check if the attacker is valid.
        An attacker is valid if it respects YACRAF multiplicities.
        """
        is_valid = len(self.abuse_cases) > 0
        if not is_valid:
            logger = logging.getLogger(__name__)
            logger.warning(f"Attacker id:{self.data[String.ID]} is not valid: it has no abuse cases")
        return is_valid
    
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
