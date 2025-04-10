# allow forward references for type hints
from __future__ import annotations

import json
import logging
from tqdm import tqdm
from model import Model
from blocks_gui.general_gui import *
from thesis_constants import *
from Tree import Tree
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def create_attack_graphs(model, attack_graph_file: str):
    """
    INPUTS: model - YACRAF Model instance
            attack_graph_file - name of a json file containing an attack graph from a compiled MAL DSL
    SIDE-EFFECT: instanciate a attack graphs, every asset on a new setup view
    """

    # read the file into a tree representation
    attack_trees : list[Tree] = file_to_trees(attack_graph_file)
    tree = attack_trees[0]
    #print(f"{tree.size()=} {tree.width()=}")
    tree.plot(model)

def parse_json(filename: str) -> tuple[
    dict[str, Any],  # attack_events
    list[dict[str, Any]],  # attackers
    list[dict[str, Any]],  # abuse_cases
    list[dict[str, Any]],  # loss_events
    list[dict[str, Any]]   # actors
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
        attack_events ={str(attack_event[String.ID]): attack_event for name, attack_event in data[String.ATTACK_STEPS].items()}
        attackers =   [attacker for name, attacker in data[String.ATTACKERS].items()]
        abuse_cases = [abuse_case for name, abuse_case in data[String.ABUSE_CASES].items()]
        loss_events = [loss_event for name, loss_event in data[String.LOSS_EVENTS].items()]
        actors = [actor for name, actor in data[String.ACTORS].items()]
 
    return attack_events, attackers, abuse_cases, loss_events, actors

def file_to_trees(filename: str) -> list:
    """
    INPUTS: filename - name of a yaml file containing an attack graph from a compiled MAL DSL
    OUTPUT: a tree representation of the attack graph
    """

    attack_events, attackers, abuse_cases, loss_events, actors = parse_json(filename)

    # inventory all unique asset names TODO remove?
    assets = set([attack_event[String.ASSET] for id, attack_event in attack_events.items()])

    # for each asset, build full attack trees
    # start from a root and spread to children upon addition of any new node
    roots = [attack_event for id, attack_event in attack_events.items() if not attack_event[String.PARENTS] and not attack_event[String.TYPE] == String.DEFENSE]

    trees = []
    start_position = (0,0)
    for root in roots:
        related_abuse_cases = [abuse_case for abuse_case in abuse_cases if str(root[String.ID]) in abuse_case[String.ATTACK_STEPS]]
        related_loss_events = [loss_event for loss_event in loss_events if str(root[String.ID]) in loss_event[String.ATTACK_STEPS]]
        related_defenses = [attack_event for id, attack_event in attack_events.items() if attack_event[String.TYPE] == String.DEFENSE and root[String.ASSET] == attack_event[String.ASSET]]

        tree = Tree(start_position, related_defenses, related_abuse_cases, related_loss_events, attackers, actors)
        tree.build(root, attack_events)
        tree.compute_grid_coordinates()
        #start_position = (tree.width(), 0)
        trees.append(tree)

    return trees

