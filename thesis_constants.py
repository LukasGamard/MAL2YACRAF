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
    """String constants"""
    NEWLINE = "\n"

    # items in the attack_graph.json
    ATTACK_STEPS = "attack_steps"
    ATTACKERS = "attackers"
    ABUSE_CASES = "abuse_cases"
    LOSS_EVENTS = "loss_events"
    ACTORS = "actors"

    # attack step's attributes
    NAME = "name"
    ID = "id"
    ASSET = "asset"
    PARENTS = "parents"
    TYPE = "type"
    AND = "and"
    OR = "or"
    DEFENSE= "defense"
    CHILDREN = "children"

    # attacker's attributes
    PERSONAL_RISK_TOLERANCE = "personal_risk_tolerance"
    CONCERN_FOR_COLLATERAL_DAMAGE = "concern_for_collateral_damage"
    SKILL = "skill"
    RESOURCES = "resources"
    SPONSORSHIP = "sponsorship"

    # abuse case's attributes
    WINDOW_OF_OPPORTUNITY = "window_of_opportunity"
    ABILITY_TO_REPUDOATE = "ability_to_repudiate"
    PERCEIVED_DETERRENCE = "perceived_deterrence"
    PERCEIVED_BENEFIT_OF_SUCCESS = "perceived_benefit_of_success"

    # loss event's attributes
    MAGNITUDE = "magnitude"

    # actor's attribute's values
    EXTERNAL = "external"
    INTERNAL = "internal"

class Units(int, Enum):
    """Numerical constants used for plotting in the YACRAF calculator"""
    # TODO change to universal block width?
    ATTACK_EVENT_WIDTH = 11
    ATTACK_EVENT_HEIGHT = 5
    DEFENSE_MECHANISM_WIDTH = 11
    DEFENSE_MECHANISM_HEIGHT = 3
    LOSS_EVENT_HEIGHT = 3
    LOSS_EVENT_WIDTH = 11
    ABUSE_CASE_HEIGHT = 8
    ABUSE_CASE_WIDTH = 11
    SIMPLE_VERTICAL_PADDING = 2
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