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
    # TODO split by usecase
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
    LOCAL_DIFFICULTY = "local_difficulty"

    # attacker's attributes
    PERSONAL_RISK_TOLERANCE = "personal_risk_tolerance"
    CONCERN_FOR_COLLATERAL_DAMAGE = "concern_for_collateral_damage"
    SKILL = "skill"
    RESOURCES = "resources"
    SPONSORSHIP = "sponsorship"

    # abuse case's attributes
    ACCESSIBILITY_TO_ATTACK_SURFACE = "accessibility_to_attack_surface"
    WINDOW_OF_OPPORTUNITY = "window_of_opportunity"
    ABILITY_TO_REPUDIATE = "ability_to_repudiate"
    PERCEIVED_DETERRENCE = "perceived_deterrence"
    PERCEIVED_BENEFIT_OF_SUCCESS = "perceived_benefit_of_success"
    PERCEIVED_EASE_OF_ATTACK = "perceived_ease_of_attack"
    EFFORT_SPENT = "effort_spent"
    ATTACKER = "attacker"

    # defense mechanism's attributes
    COST = "cost"
    IMPACT = "impact"

    # loss event's attributes
    MAGNITUDE = "magnitude"
    ACTOR = "actor"

    # actor's attribute's values
    EXTERNAL = "external"
    INTERNAL = "internal"

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

class Loss_event_setup_attribute(int, Enum):
    """Indices of setup attributes in a loss event"""
    TYPE = 0
    MAGNITUDE = 1

class Actor_setup_attribute(int, Enum):
    """Indices of setup attributes in an actor"""
    TYPE = 0

class Attacker_setup_attribute(int, Enum):
    """Indices of setup attributes in an attacker"""
    PERSONAL_RISK_TOLERANCE = 0
    CONCERN_FOR_COLLATERAL_DAMAGE = 1
    SKILL = 2
    RESOURCES = 3
    SPONSORSHIP = 4

class Abuse_case_setup_attribute(int, Enum):
    """Indices of setup attributes in an abuse case"""
    ACCESSIBILITY_TO_ATTACK_SURFACE = 0
    WINDOW_OF_OPPORTUNITY = 1
    ABILITY_TO_REPUDIATE = 2
    PERCEIVED_DETERRENCE = 3
    PERCEIVED_EASE_OF_ATTACK = 4
    PERCEIVED_BENEFIT_OF_SUCCESS = 5
    EFFORT_SPENT = 8 # see YACRAF metamodel