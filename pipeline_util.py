# allow forward references for type hints
from __future__ import annotations

import json
from pipeline_constants import *
from YacrafModel import YacrafModel, AttackEvent, Defense, Actor, AbuseCase, LossEvent, Attacker
from typing import Any, Iterable

def create_yacraf_model(model, file_path: str):
    """
    INPUTS: model - YACRAF Model instance
            file_path - name of a json file describing a YACRAF instance
    SIDE-EFFECT: instanciate the YACRAF instance and plot it in the calculator
    """
    # read the file into a tree representation
    yacraf_instance : YacrafModel = file_to_yacraf_instance(file_path)
    yacraf_instance.plot(model)

def parse_json(filename: str) -> tuple[
    dict[int, AttackEvent],  # attack_events
    dict[int, Defense],  # defenses
    dict[int, Attacker],  # attackers
    dict[int, AbuseCase],  # abuse_cases
    dict[int, LossEvent],  # loss_events
    dict[int, Actor]   # actors
]:
    """
    INPUTS: path to attack_graph.json
    OUTPUTS: parsed json ojects representing the different items present in attack_graph.json
    """
    with open(filename) as file:
        data = json.load(file)       
        # The json file is a list of attack_events, each with its children
        # We want to reorganize this into a tree

        # create a dictionary "id": "attack_event", keeping childless nodes separate. Used in AttackStep.__add_children_nodes()
        # use str() because children ids are strings, avoids later typecast
        attack_events = {int(attack_event[String.ID]):AttackEvent(attack_event) for name, attack_event in data[String.ATTACK_STEPS].items() if not attack_event[String.TYPE] == String.DEFENSE}
        # create a dictionary "id": "defense", keeping childless nodes separate
        defenses = {int(attack_event[String.ID]):Defense(attack_event) for name, attack_event in data[String.ATTACK_STEPS].items() if attack_event[String.TYPE] == String.DEFENSE}
        attackers = {int(attacker[String.ID]):Attacker(attacker) for  name, attacker in data[String.ATTACKERS].items()}
        abuse_cases = {int(abuse_case[String.ID]):AbuseCase(abuse_case) for name, abuse_case in data[String.ABUSE_CASES].items()}
        loss_events = {int(loss_event[String.ID]):LossEvent(loss_event) for name, loss_event in data[String.LOSS_EVENTS].items()}
        actors = {int(actor[String.ID]):Actor(actor) for name, actor in data[String.ACTORS].items()}

    return attack_events, defenses, attackers, abuse_cases, loss_events, actors

def file_to_yacraf_instance(filename: str) -> list:
    """
    INPUTS: filename - name of a yaml file containing an attack graph from a compiled MAL DSL
    OUTPUT: a tree representation of the attack graph
    """

    attack_events, defenses, attackers, abuse_cases, loss_events, actors = parse_json(filename)

    attack_tree_roots = [attack_event for id, attack_event in attack_events.items() if not attack_event.data[String.PARENTS]]

    yacraf_instance = YacrafModel(attack_tree_roots, attack_events, defenses, abuse_cases, loss_events, attackers, actors)

    return yacraf_instance

