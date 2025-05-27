# allow forward references for type hints
from __future__ import annotations

import json
from thesis_constants import *
from YacrafModel import YacrafModel
from typing import Any, Iterable

def create_attack_graphs(model, attack_graph_file: str):
    """
    INPUTS: model - YACRAF Model instance
            attack_graph_file - name of a json file containing an attack graph from a compiled MAL DSL
    SIDE-EFFECT: instanciate a attack graphs, every asset on a new setup view
    """

    # read the file into a tree representation
    yacraf_instance : YacrafModel = file_to_yacraf_instance(attack_graph_file)
    if yacraf_instance.isValid():
        # isValid() recursively notifies the user of all possible incompatibilities with the YACRAF model
        yacraf_instance.plot(model)

def parse_json(filename: str) -> tuple[
    dict[str, Any],  # attack_events
    dict[str, Any],  # attackers
    dict[str, Any],  # abuse_cases
    dict[str, Any],  # loss_events
    Iterable[dict[str, Any]]   # actors
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
        attack_events = {str(attack_event[String.ID]): attack_event for name, attack_event in data[String.ATTACK_STEPS].items()}
        attackers = data[String.ATTACKERS]
        abuse_cases = {str(abuse_case[String.ID]): abuse_case for name, abuse_case in data[String.ABUSE_CASES].items()}
        loss_events = {str(loss_event[String.ID]): loss_event for name, loss_event in data[String.LOSS_EVENTS].items()}
        actors = data[String.ACTORS].values()
 
    return attack_events, attackers, abuse_cases, loss_events, actors

def file_to_yacraf_instance(filename: str) -> list:
    """
    INPUTS: filename - name of a yaml file containing an attack graph from a compiled MAL DSL
    OUTPUT: a tree representation of the attack graph
    """

    attack_events, attackers, abuse_cases, loss_events, actors = parse_json(filename)

    attack_tree_roots = [attack_event for id, attack_event in attack_events.items() if not attack_event[String.PARENTS] and not attack_event[String.TYPE] == String.DEFENSE]
    defenses = [attack_event for id, attack_event in attack_events.items() if attack_event[String.TYPE] == String.DEFENSE]

    yacraf_instance = YacrafModel(attack_tree_roots, attack_events, defenses, abuse_cases, loss_events, attackers, actors)


    return yacraf_instance

