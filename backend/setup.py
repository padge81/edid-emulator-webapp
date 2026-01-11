# Import required modules
import os
import shutil

# Define the directory path
dir_path = os.path.dirname(__file__)

# Define the edid-rw directory and files
edid_rw_dir = os.path.join(dir_path, 'edid-rw')
edid_rw_files = ['edid-rw', 'edid-decode']

# Check if the edid-rw directory exists
if not os.path.exists(edid_rw_dir):
    # If not, create the directory and copy the files
    os.makedirs(edid_rw_dir)
    for file in edid_rw_files:
        shutil.copyfile(os.path.join(dir_path, file), os.path.join(edid_rw_dir, file))

# Print a success message
print(f"Setup complete. edid-rw directory and files have been created in {edid_rw_dir}")