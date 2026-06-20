import subprocess
import sys
import os

#Create data directory if it doesn't exist
directory = "./data"
os.makedirs(directory, exist_ok = True)


SCRIPTS = [
    './download_sets.py',
    './append_abc_incipits_to_sets_full.py',
    './session_sets.py',
]

for i, script in enumerate(SCRIPTS, 1):
    print(f"\n{'='*60}")
    print(f"[{i}/{len(SCRIPTS)}] Running: {script}")
    print('='*60)

    result = subprocess.run(
        [sys.executable, script],
        # Inherit the current process's stdout/stderr so output streams live
        stdout=None,
        stderr=None,
    )

    if result.returncode != 0:
        print(f"\n✗ Script failed with exit code {result.returncode}. Stopping pipeline.")
        sys.exit(result.returncode)

    print(f"\n✓ Completed: {script}")

print(f"\n{'='*60}")
print("✓ All scripts completed successfully.")
print('='*60)