with open('scripts/run_app.py', 'r') as f:
    lines = f.readlines()

fixed = []
i = 0
while i < len(lines):
    line = lines[i]
    # Find the broken IBS Exit log line (unterminated, followed by closing `")` on next line)
    if 'IBS Exit' in line and i + 1 < len(lines) and lines[i+1].strip() == '")':
        # Join the two lines, inserting \n before the closing quote
        merged = line.rstrip('\r\n') + r'\n")' + '\n'
        fixed.append(merged)
        i += 2  # skip the orphaned `")` line
    else:
        fixed.append(line)
        i += 1

with open('scripts/run_app.py', 'w') as f:
    f.writelines(fixed)

print("Done - merged broken string literal")
