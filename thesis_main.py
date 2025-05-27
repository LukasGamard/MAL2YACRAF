import tkinter as tk
import sys
import os
from logger_config import setup_logging
import logging

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

sys.path.append("config")
from program_paths import *

# Set up the paths for modules that are imported elsewhere in the program
for path in IMPORT_PATHS:
    sys.path.append(path)
    
from settings import Settings

def main():
    setup_logging()  # Configure logging
    logger = logging.getLogger(__name__)
    logger.info("Application started")

    if len(sys.argv) != 2 and False:
        print(f"Usage: {sys.argv[0]} <save_name>")
        
        saves_path = os.path.join(BASE_PATH, SAVES_DIRECTORY)
        print(f"{BASE_PATH=} {SAVES_DIRECTORY=}")
        print(f"Existing saves: {[name for name in os.listdir(saves_path) if os.path.isdir(os.path.join(saves_path, name))]}")
        return
    
    
    save_name = "custom"#sys.argv[1]
    
    settings = Settings(save_name)
    settings.save()
    
    from model import Model
    
    root = tk.Tk()
    model = Model(root, num_setup_views=1)

    attack_graph_file = "mini_mini_attack_graph.json"
    
    from thesis_util import create_attack_graphs
    create_attack_graphs(model, attack_graph_file)
    
    # clean up the default model. Need to be done after the model is created
    # since the model needs to have at least one setup view to be valid
    setup_views = model.get_setup_views()
    # delete the first 3 setup views (those are empty by default)
    for setup_view in list(setup_views):
        if setup_view.get_name() in ["Setup 1", "Setup 2", "Setup 3"]:         
            model.delete_view(setup_view)
    setup_view = model.get_setup_views()[0]
    model.change_view(setup_view)
    root.mainloop()
    
if __name__ == "__main__":
    main()

