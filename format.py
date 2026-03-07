with open("jp_sector_app.py", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if len(line) >= 4 and line[:4] == "    ":
        new_lines.append(line[4:])
    elif line.strip() == "def main():" or line.strip() == "import streamlit as st" or line.strip() == "if __name__ == \"__main__\":" \
        or line[:6] == "import" or line[:4] == "from":
        new_lines.append(line)
    elif line.strip():
        pass # delete anything else that was dedented but not part of header
    else:
        new_lines.append(line)

# Let's just fix the broken line via sed
