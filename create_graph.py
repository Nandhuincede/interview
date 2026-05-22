from app.interview_workflow.workflow import graph_flow

# Create workflow
flow = graph_flow()

# Generate PNG image bytes
graph_image = flow.get_graph().draw_mermaid_png()

# Save image
with open("graph_image.png", "wb") as f:
    f.write(graph_image)

print("Graph image generated successfully!")