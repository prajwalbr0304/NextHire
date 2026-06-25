import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
ranker_path = os.path.join(script_dir, 'ranker.py')

# Read the file
with open(ranker_path, 'r') as f:
    lines = f.readlines()

# Check if staged function already exists
content = ''.join(lines)
if 'def staged()' in content:
    print('staged function already exists')
else:
    # Find line 109 (0-indexed: 108) - the closing brace of status() function
    # Looking for the line that ends the status function: "    }"
    insertion_index = None
    for i, line in enumerate(lines):
        # Find the line after status() function ends (after the closing brace on line 109)
        # Looking for the pattern:  line contains just "}" and is after status function
        if i >= 108 and i <= 111 and line.strip() == '}':
            insertion_index = i + 1
            break
    
    if insertion_index is not None:
        staged_func = '''

# ---------------------------------------------------------------------------
# Get staged file info (for frontend state persistence on refresh)
# ---------------------------------------------------------------------------
def staged() -> dict:
    return {
        "name": STAGED.get("name"),
        "size_mb": STAGED.get("size_mb"),
        "path": STAGED.get("path"),
    }

'''
        new_lines = lines[:insertion_index] + [staged_func] + lines[insertion_index:]
        with open(ranker_path, 'w') as f:
            f.writelines(new_lines)
        print('Added staged function successfully')
    else:
        print('Could not find insertion point')
        # Let's print lines around 108-115
        for i in range(105, 116):
            print(f"{i+1}: {lines[i]}")