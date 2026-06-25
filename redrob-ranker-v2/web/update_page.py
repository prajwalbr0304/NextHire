import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
page_path = os.path.join(script_dir, 'app', 'page.tsx')

# Read the file
with open(page_path, 'r') as f:
    content = f.read()

# Check if api.staged() call already exists
if 'api.staged()' in content:
    print('api.staged() call already exists')
else:
    # Find the init useEffect and add the staged call
    # Look for the pattern: api.status().then((s) => { setStatus(s); if (s.status === "done") refreshAll(); }).catch(() => {});
    target = '''    api.status().then((s) => { setStatus(s); if (s.status === "done") refreshAll(); }).catch(() => {});
    api.logs().then((r) => setBeLogs(r.logs)).catch(() => {});'''

    replacement = '''    api.status().then((s) => { setStatus(s); if (s.status === "done") refreshAll(); }).catch(() => {});
    // Restore staged file info on page refresh
    api.staged().then((stagedData) => {
      if (stagedData.name && stagedData.size_mb) {
        setStaged({ name: stagedData.name, size_mb: stagedData.size_mb });
        // Also set hasRanked to true if there was a previous ranking (status is done)
        api.status().then((s) => {
          if (s.status === "done") {
            setHasRanked(true);
            refreshAll();
          }
        }).catch(() => {});
      }
    }).catch(() => {});
    api.logs().then((r) => setBeLogs(r.logs)).catch(() => {});'''

    new_content = content.replace(target, replacement)
    
    if new_content == content:
        print('Could not find target pattern')
        # Let's print the init effect section
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'api.status().then' in line:
                print(f"Found api.status at line {i+1}")
                for j in range(max(0, i-2), min(len(lines), i+10)):
                    print(f"{j+1}: {lines[j]}")
                break
    else:
        with open(page_path, 'w') as f:
            f.write(new_content)
        print('Added api.staged() call successfully')