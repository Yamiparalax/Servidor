import shutil
import os
from pathlib import Path

# Path to the node folder
node_dir = Path("binaries/node")
zip_path = Path("binaries/node_bundle") # shutil.make_archive adds .zip

print("Zipping Node.js binaries...")
if node_dir.exists():
    shutil.make_archive(str(zip_path), 'zip', root_dir="binaries", base_dir="node")
    print(f"Created {zip_path}.zip")
else:
    print("Node dir not found!")
