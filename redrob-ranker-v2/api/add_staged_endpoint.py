import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
main_path = os.path.join(script_dir, 'main.py')

# Read the file
with open(main_path, 'r') as f:
    content = f.read()

# Check if endpoint already exists
if '/api/staged' in content:
    print('staged endpoint already exists')
else:
    # Find the position after @app.get("/api/status") and add our endpoint
    # Look for the pattern: @app.get("/api/status")\ndef get_status():\n    return ranker.status()
    target = '''@app.get("/api/status")
def get_status():
    return ranker.status()'''

    replacement = '''@app.get("/api/status")
def get_status():
    return ranker.status()


@app.get("/api/staged")
def get_staged():
    return ranker.staged()'''

    new_content = content.replace(target, replacement)
    
    if new_content == content:
        print('Could not find target pattern')
        # Print lines around the status endpoint
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '/api/status' in line:
                print(f"Found /api/status at line {i+1}")
                for j in range(max(0, i-2), min(len(lines), i+8)):
                    print(f"{j+1}: {lines[j]}")
                break
    else:
        with open(main_path, 'w') as f:
            f.write(new_content)
        print('Added staged endpoint successfully')