# allow forward references for type hints
from __future__ import annotations
import sys
import json
from pipeline_constants import *
from YacrafModel import YacrafModel, AttackEvent, Defense, Actor, AbuseCase, LossEvent, Attacker
import logging
logger = logging.getLogger(__name__)

def create_yacraf_model(model, file_path: str):
    """
    INPUTS: model - YACRAF Model instance
            file_path - name of a json file describing a YACRAF instance
    SIDE-EFFECT: instanciate the YACRAF instance and plot it in the calculator
    """
    # read the file into a tree representation
    yacraf_instance : YacrafModel = file_to_yacraf_instance(file_path)
    if yacraf_instance.isValid():
        yacraf_instance.plot(model)
    else:
        logger.error("The YACRAF instance is not valid. Please check the input file. See logs for more information.")
        sys.exit(1)

def parse_json(filename: str) -> tuple[
    dict[int, AttackEvent],
    dict[int, Defense],
    dict[int, Attacker],
    dict[int, AbuseCase],
    dict[int, LossEvent],
    dict[int, Actor]
]:
    """
    INPUTS: path to attack_graph.json
    OUTPUTS: parsed json ojects representing the different items present in attack_graph.json
    """
    with open(filename) as file:
        data = json.load(file)

        # Convert the data into the appropriate classes
        attack_events = {int(attack_event[String.ID]):AttackEvent(attack_event) for name, attack_event in data[String.ATTACK_STEPS].items() if not attack_event[String.TYPE] == String.DEFENSE}
        defenses = {int(attack_event[String.ID]):Defense(attack_event) for name, attack_event in data[String.ATTACK_STEPS].items() if attack_event[String.TYPE] == String.DEFENSE}
        attackers = {int(attacker[String.ID]):Attacker(attacker) for  name, attacker in data[String.ATTACKERS].items()}
        abuse_cases = {int(abuse_case[String.ID]):AbuseCase(abuse_case) for name, abuse_case in data[String.ABUSE_CASES].items()}
        loss_events = {int(loss_event[String.ID]):LossEvent(loss_event) for name, loss_event in data[String.LOSS_EVENTS].items()}
        actors = {int(actor[String.ID]):Actor(actor) for name, actor in data[String.ACTORS].items()}

    #logger.debug(f'Attack Events Parsed: {attack_events}')
    return attack_events, defenses, attackers, abuse_cases, loss_events, actors

def file_to_yacraf_instance(filename: str) -> list:
    """
    INPUTS: filename - name of a yaml file containing an attack graph from a compiled MAL DSL
    OUTPUT: a tree representation of the attack graph
    """

    attack_events, defenses, attackers, abuse_cases, loss_events, actors = parse_json(filename)
    #logger.debug(f'Parsed attack_events: {attack_events}')
    root_ids = []
    logger.debug(f"Abuse cases: {abuse_cases}")
    for abuse_case in abuse_cases.values():
        logger.debug(f"Processing abuse case id:{abuse_case.data[String.ID]} with attack steps: {abuse_case.data[String.ATTACK_STEPS]}")
        for attack_step_id, attack_step_name in abuse_case.data[String.ATTACK_STEPS].items():
            if attack_step_id not in root_ids:
                root_ids.append(attack_step_id)
    logger.debug(f'Identified root attack event IDs from abuse cases: {root_ids}')
    attack_tree_roots = [attack_event for id, attack_event in attack_events.items() if str(id) in root_ids]
    logger.debug(f'Attack tree roots: {[root.data[String.ID] for root in attack_tree_roots]}')
    yacraf_instance = YacrafModel(attack_tree_roots, attack_events, defenses, abuse_cases, loss_events, attackers, actors)

    return yacraf_instance

