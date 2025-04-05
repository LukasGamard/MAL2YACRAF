from enum import Enum

class Metamodel(int, Enum):
    YACRAF_1 = 0
    YACRAF_2 = 1

class Configuration_classes_gui(int, Enum):
    """Indices of configruration_classes_gui on the YACRAF metamodel 1"""
    ATTACK_EVENT_AND = 0
    ATTACK_EVENT_OR = 1
    ABUSE_CASE = 2
    ATTACKER = 3
    LOSS_EVENT = 4
    ACTOR = 5
    DEFENSE_MECHANISM = 6


class String(str, Enum):
    """String constants used in the attack_graph.json"""
    NAME = "name"
    NEWLINE = "\n"
    ATTACK_STEPS = "attack_steps"
    ID = "id"
    ASSET = "asset"
    PARENTS = "parents"
    TYPE = "type"
    AND = "and"
    OR = "or"
    DEFENSE= "defense"
    CHILDREN = "children"

class Units(int, Enum):
    """Constants used for plotting in the YACRAF calculator"""
    ATTACK_EVENT_WIDTH = 11
    ATTACK_EVENT_HEIGHT = 5
    DEFENSE_MECHANISM_WIDTH = 11
    DEFENSE_MECHANISM_HEIGHT = 3
    VERTICAL_PADDING = 4
    HORIZONTAL_PADDING = 2

class Attack_event_setup_attribute(int, Enum):
    """Indices of setup attributes in an attack event"""
    TYPE = 0
    LOCAL_DIFFICULTY = 1
    GLOBAL_DIFFICULTY = 2
    PROBABILITY_OF_SUCCESS = 3

class Defense_setup_attribute(int, Enum):
    """Indices of etup attributes in a defense mechanism"""
    COST = 0
    IMPACT = 1