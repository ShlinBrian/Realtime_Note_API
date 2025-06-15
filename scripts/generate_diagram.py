#!/usr/bin/env python3
"""
Generate architecture diagram from Mermaid code
Requires: pip install mermaid-cli (needs Node.js)
"""

import subprocess
import os


def generate_diagram():
    """Generate PNG from Mermaid markdown file"""
    input_file = "docs/architecture_flowchart.md"
    output_file = "docs/architecture_diagram.png"

    try:
        # Extract mermaid content from markdown
        with open(input_file, "r") as f:
            content = f.read()

        # Find the first mermaid block
        start = content.find("```mermaid\n") + len("```mermaid\n")
        end = content.find("\n```", start)
        mermaid_code = content[start:end]

        # Write pure mermaid file
        mermaid_file = "temp_diagram.mmd"
        with open(mermaid_file, "w") as f:
            f.write(mermaid_code)

        # Generate image (requires mermaid-cli: npm install -g @mermaid-js/mermaid-cli)
        cmd = f"mmdc -i {mermaid_file} -o {output_file} -t dark -b transparent"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Diagram generated: {output_file}")
        else:
            print(f"❌ Error: {result.stderr}")
            print("💡 Install mermaid-cli: npm install -g @mermaid-js/mermaid-cli")

        # Cleanup
        os.remove(mermaid_file)

    except FileNotFoundError:
        print(f"❌ File not found: {input_file}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    generate_diagram()
