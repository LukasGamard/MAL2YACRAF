import tkinter as tk
import sys
import os
import json
from pipeline_logger_config import setup_logging
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

    # Ensure the user provided an argument
    if len(sys.argv) != 2 and False:
        print("Usage: python script.py <file_path>")
        sys.exit(1)
    
    # Get the file path from the command-line argument
    file_path = "mini_attack_graph.json"#sys.argv[1]

    # Check if the file is a valid JSON file
    if not is_json_file(file_path):
        print(f"The file '{file_path}' is not a valid JSON file.")
        sys.exit(1)

    # Use this existing save as a starting point   
    save_name = "custom"
    
    settings = Settings(save_name)
    settings.save()
    
    from model import Model
    
    root = tk.Tk()
    model = Model(root, num_setup_views=1)

    from pipeline_util import create_yacraf_model
    create_yacraf_model(model, file_path)
    
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

def is_json_file(filepath):
    # Check if the file has a .json extension
    if not filepath.endswith('.json'):
        print(f"The file '{filepath}' does not have a .json extension.")
        return False
    
    # Check if the file exists
    if not os.path.isfile(filepath):
        print(f"The file '{filepath}' does not exist.")
        return False
    
    # Try to load the file as JSON
    try:
        with open(filepath, 'r') as file:
            json.load(file)
    except json.JSONDecodeError:
        print(f"The file '{filepath}' is not a valid JSON file.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

    return True

if __name__ == "__main__":
    main()

