import os
import glob
Import("env")

print("\n[WORKAROUND] Searching for accidental duplicate file 'decoder_util copy.c'...\n")

# PlatformIO stores downloaded libraries in either .pio or .piolibdeps
search_paths = [
    os.path.join(env.get("PROJECT_WORKSPACE_DIR", ".pio"), "**", "decoder_util copy.c"),
    os.path.join(env.get("PROJECT_DIR", ""), ".piolibdeps", "**", "decoder_util copy.c")
]

for path in search_paths:
    for file_path in glob.glob(path, recursive=True):
        if os.path.exists(file_path):
            print(f"-> Deleting duplicate to fix build: {file_path}")
            os.remove(file_path)
