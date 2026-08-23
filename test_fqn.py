import os
import pathlib

def build_class_to_file_map(root_dir: str):
    mapping = {}
    for root, _, files in os.walk(root_dir):
        for f in files:
            if f.endswith('.java'):
                full_path = os.path.join(root, f)
                # Read file to find package and class
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    
                # naive parsing:
                package_name = ""
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith("package "):
                        package_name = line.replace("package ", "").replace(";", "").strip()
                        break
                        
                class_name = f.replace(".java", "")
                if package_name:
                    fqn = f"{package_name}.{class_name}"
                else:
                    fqn = class_name
                    
                mapping[fqn] = os.path.relpath(full_path, start=os.getcwd())
    return mapping

m = build_class_to_file_map("ATM-Simulator-System")
import json
print(json.dumps(m, indent=2))
