with open('scripts/run_app.py', 'r') as f:
    lines = f.readlines()

for i in range(len(lines)):
    if 'return "\\n".join(output)' in lines[i]:
        if 'trades' in lines[i]:
            lines[i] = lines[i].replace(', trades', ', []')
        elif '[]' not in lines[i]:
            lines[i] = lines[i].replace('return "\\n".join(output)', 'return "\\n".join(output), []')

# Find the last return and ensure it returns trades
last_return_idx = -1
for i in range(len(lines)):
    if 'return "\\n".join(output)' in lines[i]:
        last_return_idx = i

if last_return_idx != -1:
    lines[last_return_idx] = '    return "\\n".join(output), trades\n'

with open('scripts/run_app.py', 'w') as f:
    f.writelines(lines)
print("Done")
