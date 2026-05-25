# app/interview_workflow/agents/generate_graph.py
from app.interview_workflow.workflow import graph_flow

compiled_graph = graph_flow()
graph_image    = compiled_graph.get_graph().draw_mermaid_png()

with open("graph_image.png", "wb") as f:
    f.write(graph_image)

print("Graph image generated successfully!")
