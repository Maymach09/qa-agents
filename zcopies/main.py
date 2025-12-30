import asyncio
from src.graph.workflow import build_graph
from langchain_core.runnables.graph import MermaidDrawMethod

Pages = """
    1. Home Page.
        url: https://computing-ability-8321.lightning.force.com/lightning/page/home

    2. Accounts Page.
        url: https://computing-ability-8321.lightning.force.com/lightning/o/Account/list?filterName=Recent

    3. New Account form page.
        url: https://computing-ability-8321.lightning.force.com/lightning/o/Account/new
"""

user_story = """
    User should be able to navigate to the Accounts page from the home page by clicking on the 'Accounts' link in the main navigation menu.
    User should be able to open the 'New' account form and add a New Account by filling out the account form by filling all the mandatory fields and submitting it.
    User should be able to view the recently created Accounts in the Accounts list view.
"""

app = build_graph()

inputs = {
    "messages": [
        (
            "user",
            f"""
Pages:
{Pages}

User Story:
{user_story}
"""
        )
    ]
}

async def main():
    # Set higher recursion limit to accommodate healing loop (up to 3 iterations)
    # Snapshot (5-10) + Planner (1) + Designer (1) + Generator (1) + Runner+Healer (6 for 3 iterations) = ~20-25
    # Setting to 50 to be safe
    config = {"recursion_limit": 50}
    
    async for event in app.astream(inputs, stream_mode="values", config=config):
        event["messages"][-1].pretty_print()



###################################################################
# Save graph as PNG
try:
    png_data = app.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
    with open("workflow_graph.png", "wb") as f:
        f.write(png_data)
    print("\n✅ Graph saved as workflow_graph.png")
except Exception as e:
    print(f"\n⚠️  Could not save PNG: {e}")
    print("Falling back to text output...")

# Visualize graph structure
print("\n" + "="*50)
print("GRAPH STRUCTURE")
print("="*50)
print(app.get_graph().draw_mermaid())
print("\nCopy the output above and paste at https://mermaid.live to visualize")
print("="*50 + "\n")
####################################################################



if __name__ == "__main__":
    asyncio.run(main())