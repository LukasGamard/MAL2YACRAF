import tkinter as tk
import sys
import os

METAMODEL_YACRAF_1 = 0
METAMODEL_YACRAF_2 = 1

ATTACK_EVENT_AND = 0
ATTACK_EVENT_OR = 1

sys.path.append("config")
from program_paths import *

# Set up the paths for modules that are imported elsewhere in the program
for path in IMPORT_PATHS:
    sys.path.append(path)
    
from settings import Settings
from general_gui import *
from thesis_util import *

def main():
    if len(sys.argv) != 2 and False:
        print(f"Usage: {sys.argv[0]} <save_name>")
        
        saves_path = os.path.join(BASE_PATH, SAVES_DIRECTORY)
        print(f"Existing saves: {[name for name in os.listdir(saves_path) if os.path.isdir(os.path.join(saves_path, name))]}")
        return
    
    save_name = "custom"#sys.argv[1]
    
    settings = Settings(save_name)
    settings.save()
    
    from model import Model
    
    root = tk.Tk()
    model = Model(root, num_setup_views=1)

    attack_graph_file = "attack_graph.json"
    create_attack_graph(model, attack_graph_file)
    
    setup_view = model.get_setup_views()[0]
    configuration_view = model.get_configuration_views()[METAMODEL_YACRAF_2]
    configuration_classes_gui = configuration_view.get_configuration_classes_gui()
    # avoid stacking
    positions = get_block_start_coordinates(setup_view.get_length_unit(), num_coordinates=2)
    setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[ATTACK_EVENT_AND], position=positions[0])
    setup_view.create_setup_class_gui(configuration_class_gui=configuration_classes_gui[ATTACK_EVENT_OR], position=positions[1])

    setup_view.create_connection_with_blocks(start_coordinate=positions[0], end_coordinate=positions[1])
    model.change_view(setup_view)
    root.mainloop()
    
if __name__ == "__main__":
    main()

