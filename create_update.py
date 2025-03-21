import os
import sys
import shutil
from update_manager import create_update_package

# Current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the executable
exe_path = os.path.join(current_dir, "dist", "Hoesway.exe")

if not os.path.exists(exe_path):
    print(f"Error: Could not find executable at {exe_path}")
    sys.exit(1)

print(f"Creating update package using executable: {exe_path}")

# Create the update package
create_update_package(
    version="0.7.0",
    executable_path=exe_path,
    release_notes="Version 0.7.0 updates:\n- Implemented local update system\n- Fixed UI initialization issues\n- Added file management features\n- Enhanced user experience"
)

print("Update package created successfully!")
print("You can now run the original executable to test the update process.")
