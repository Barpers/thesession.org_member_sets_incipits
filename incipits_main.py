import subprocess
import sys
import os

#Create data directory if it doesn't exist
directory = "./data"
os.makedirs(directory, exist_ok = True)

default_member_id = 179479 #barper's member ID

def check_argument(x):
    # Ensure an argument was passed (sys.argv[0] is always the script name)
    if len(sys.argv) < 2:
        print("No argument provided. Barpers member ID will be used as default (179479).")
        return x

    arg = sys.argv[1]

    try:
        # Try converting to a float (handles integers and decimals)
        num = float(arg)
        #print(f"Success! '{arg}' is numeric: {num}")
        return int(num)
    except ValueError:
        print(f"Error: '{arg}' is not a valid number.\n Try again with a TheSession member ID (e.g., 179479)\n or enter no member ID, and we will use the default (179479).")
        return None
    
member_id = check_argument(default_member_id)
if member_id is None:             
    sys.exit(0)  # Exit the script with an error code if the argument is invalid
else:
    #member_id = check_argument(default_member_id)
    print(f"Using member ID: {member_id}")  

SCRIPTS = [
    './download_sets.py',
    './append_abc_incipits_to_sets_full.py',
    './session_sets.py'
]



for i, script in enumerate(SCRIPTS, 1):
    print(f"\n{'='*60}")
    print(f"[{i}/{len(SCRIPTS)}] Running: {script} with member ID: {member_id}")
    print('='*60)

    result = subprocess.run(
        [sys.executable, script] + [str(member_id)],  # Pass the member_id as an argument to the script
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