# allow forward references for type hints
from __future__ import annotations

import json
import logging
from tqdm import tqdm
from views.configuration_view import ConfigurationView
from blocks_gui.configuration.configuration_class_gui import GUIConfigurationClass
from model import Model
from blocks_gui.general_gui import *
from thesis_constants import *
from Tree import Tree

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
    print(f"{tree.size()=} {tree.width()=}")
    #a=1
    # generate the model
    tree_to_setup_view(model, tree)

def parse_json(filename: str):
    """
    INPUTS: path to attack_graph.json
    OUTPUTS: parsed json ojects representing the different items present in attack_graph.json
    """
    with open(filename) as file:
        data = json.load(file)       
        # The json file is a list of attack_steps, each with its children
        # We want to reorganize this into a tree

        # create a dictionary "id": "attack_step", keeping childless nodes separate
        # use str() because children ids are strings, avoids later typecast
        attack_steps = {str(attack_step[String.ID]): attack_step for name, attack_step in data[String.ATTACK_STEPS].items()}
        attackers = {str(attacker[String.ID]): attacker for name, attacker in data[String.ATTACKERS].items()}
        abuse_cases = {str(abuse_case[String.ID]): abuse_case for name, abuse_case in data[String.ABUSE_CASES].items()}
        loss_events = {str(loss_event[String.ID]): loss_event for name, loss_event in data[String.LOSS_EVENTS].items()}
        actors = {str(actor[String.ID]): actor for name, actor in data[String.ACTORS].items()}
 
    return attack_steps, attackers, abuse_cases, loss_events, actors

def file_to_trees(filename: str) -> list:
    """
    INPUTS: filename - name of a yaml file containing an attack graph from a compiled MAL DSL
    OUTPUT: a tree representation of the attack graph
    """

    attack_steps, attackers, abuse_cases, loss_events, actors = parse_json(filename)

    # inventory all unique asset names
    assets = set([attack_step[String.ASSET] for id, attack_step in attack_steps.items()])

    # for each asset, build full attack trees
    # start from a root and spread to children upon addition of any new node
    roots = [atk_step for id, atk_step in attack_steps.items() if not atk_step[String.PARENTS] and not atk_step[String.TYPE] == String.DEFENSE]
    defenses = [atk_step for id, atk_step in attack_steps.items() if atk_step[String.TYPE] == String.DEFENSE]

    trees = []
    start_position = (0,0)
    for root in roots:
        related_abuse_cases = [abuse_case for id, abuse_case in abuse_cases.items() if str(root[String.ID]) in abuse_case[String.ATTACK_STEPS]]
        related_loss_events = [loss_event for id, loss_event in loss_events.items() if str(root[String.ID]) in loss_event[String.ATTACK_STEPS]]
        tree = Tree(start_position, related_abuse_cases, related_loss_events)
        tree.include_defenses(defenses, root[String.ASSET]) # need to add defenses BEFORE adding Nodes
        tree.build(root, attack_steps)
        tree.compute_grid_coordinates()
        start_position = (tree.get_width(), 0)
        trees.append(tree)

    return trees

def tree_to_setup_view(model: Model, tree: Tree):
    setup_view_attack_graph = model.get_setup_views()[0]
    setup_view_defenses = model.get_setup_views()[1]
    configuration_view_main : ConfigurationView = model.get_configuration_views()[Metamodel.YACRAF_1]
    configuration_classes_gui_main : list[GUIConfigurationClass]= configuration_view_main.get_configuration_classes_gui()
    tree.root.create_setup_class(setup_view_attack_graph, configuration_classes_gui_main)
    # stack abuse cases and loss event above the attack tree
    for abuse_case in tree.abuse_cases:
        abuse_case.create_setup_class(setup_view_attack_graph, configuration_classes_gui_main)
    for loss_event in tree.loss_events:
        loss_event.create_setup_class(setup_view_attack_graph, configuration_classes_gui_main)
    # TODO plot actors

    # plot defenses in another setup view
    start_position = (0, 0)
    for defense in tree.defenses:
        defense.create_setup_class(setup_view_defenses, configuration_classes_gui_main, position=start_position, model=model)
        start_position = (start_position[0] + 2*Units.VERTICAL_PADDING + 2*Units.DEFENSE_MECHANISM_WIDTH, 0)

