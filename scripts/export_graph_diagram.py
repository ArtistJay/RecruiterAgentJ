"""Export LangGraph pipeline as visual diagram."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.graph import graph

# Export as PNG (requires graphviz)
try:
    png_data = graph.get_graph().draw_mermaid_png()
    with open("docs/architecture_diagram.png", "wb") as f:
        f.write(png_data)
    print("✅ Architecture diagram saved to docs/architecture_diagram.png")
except Exception as e:
    print(f"⚠️ PNG export failed: {e}")
    print("Exporting as Mermaid text instead...")

# Always export Mermaid text (works without graphviz)
mermaid = graph.get_graph().draw_mermaid()
with open("docs/architecture_mermaid.md", "w") as f:
    f.write("# agentJ Architecture\n\n")
    f.write("```mermaid\n")
    f.write(mermaid)
    f.write("\n```\n")
print("✅ Mermaid diagram saved to docs/architecture_mermaid.md")
print("\nMermaid code:\n")
print(mermaid)
