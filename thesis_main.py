import tkinter as tk
import sys
import os
from thesis_constants import *
# TODO prettify imports (make everything a python package)
sys.path.append("config")
from program_paths import *

# Set up the paths for modules that are imported elsewhere in the program
for path in IMPORT_PATHS:
    sys.path.append(path)
    
from settings import Settings
from blocks_gui.general_gui import *
from thesis_util import *
from model import Model

def main():
    if len(sys.argv) != 2 and False:
        print(f"Usage: {sys.argv[0]} <save_name>")
        
        saves_path = os.path.join(BASE_PATH, SAVES_DIRECTORY)
        print(f"Existing saves: {[name for name in os.listdir(saves_path) if os.path.isdir(os.path.join(saves_path, name))]}")
        return
    
    save_name = "custom"#sys.argv[1]
    
    settings = Settings(save_name)
    settings.save()
    
    root = tk.Tk()
    model = Model(root, num_setup_views=1)
    # clean up the default model
    setup_views = model.get_setup_views()
    for setup_view in setup_views:
        model.delete_view(setup_view)

    attack_graph_file = "mini_attack_graph.json"
    create_attack_graphs(model, attack_graph_file)
    
    setup_view = model.get_setup_views()[0]
    model.change_view(setup_view)
    root.mainloop()
    
if __name__ == "__main__":
    main()

