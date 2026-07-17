# !/usr/bin/env python3
import os
import sys
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__)))

cmd = "uname -m && pacman-conf --repo-list"


result = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout
result_lines = result.strip().split("\n")

print("System Architecture:", result_lines[0])
print("Pacman Repositories:")
for line in result_lines[1:]:
    match line:
        case _ if line.endswith("-v3"):
            print(f"Architecture: {result_lines[0]}_v3, Repository: {line}")
        case _ if line.endswith("-v4"):
            print(f"Architecture: {result_lines[0]}_v4, Repository: {line}")
        case _:
            print(f"Architecture: {result_lines[0]}, Repository: {line}")  
        
    
