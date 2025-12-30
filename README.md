# QA Process Automation - Multi-Agent System

Automated end-to-end QA test generation using LangGraph agents and Playwright MCP.

## 🎯 Workflow

```
User Input: URL + User Story
    ↓
[1] DOM Selector Agent
    - Reads user story
    - Intelligently navigates website (LLM-guided)
    - Captures snapshots at each step
    - Saves to output/raw_dom.md
    ↓
[2] Selector Extractor Agent
    - Parses captured DOM
    - Extracts stable selectors
    - Structures as JSON
    - Saves to output/structured_dom.json
    ↓
[3] Test Planner Agent
    - Reads user story + structured DOM
    - Generates BDD test scenarios
    - Saves to output/test_plan.json
    ↓
[4] Test Generator Agent
    - Converts BDD to TypeScript
    - Uses Playwright @playwright/test
    - Saves to output/tests/test_generated.spec.ts
```

## 🚀 Usage

```bash
# 1. Start Playwright MCP server (port 5174)
# (in separate terminal)

# 2. Set environment variables
echo "GOOGLE_API_KEY=your_key_here" > .env

# 3. Run workflow
python main.py
```

## 📥 Input

```python
{
    "url": "https://demo.opencart.com/",
    "use_case": "Search for 'laptop', select first product, add to cart"
}
```

## 📤 Output

```
output/
├── raw_dom.md              # All captured pages
├── structured_dom.json     # Extracted selectors
├── test_plan.json          # BDD scenarios
└── tests/
    └── test_generated.spec.ts  # TypeScript tests
```

## 🤖 How It Works

### Agent 1: DOM Selector (Intelligent Navigation)
- Uses LLM + Playwright MCP tools
- At each page, LLM decides: click, type, or done
- Captures snapshots along the journey
- Prompt guides decision-making

### Agent 2: Selector Extractor
- Parses DOM for automation-friendly elements
- Prioritizes: data-testid, aria-label, role, id
- Assigns confidence levels

### Agent 3: Test Planner
- Creates Given/When/Then scenarios
- Maps to available elements

### Agent 4: Test Generator  
- Generates TypeScript/Playwright code
- Uses only stable selectors
- Production-ready tests

## 🔧 Requirements

```
langgraph
langchain
langchain-google-genai
langchain-mcp-adapters
python-dotenv
```

## 🎛️ Configuration

**Prompt-based behavior:** Each agent uses prompts in `src/prompts/`
- `dom_selector.txt` - Navigation decisions
- `dom_parser.txt` - Selector extraction
- `test_planner.txt` - Scenario generation
- `test_generator.txt` - Code generation

**Code-based workflow:** LangGraph in `src/graph/workflow.py`
- Deterministic flow: 1 → 2 → 3 → 4
- Each agent processes state sequentially

## 📊 Architecture

**Hybrid Approach:**
- ✅ Code controls WHEN (workflow order)
- ✅ Prompts control HOW (agent behavior)
- ✅ Best of both: Reliable + Intelligent

**State Management:**
```python
AgentState = {
    "url": str,
    "use_case": str,
    "raw_dom": str,
    "structured_dom": dict,
    "test_plan": dict,
    "playwright_tests": str
}
```

## 🐛 Troubleshooting

**"No tools returned from Playwright MCP"**
→ Start MCP server on port 5174

**"Module langchain_mcp_adapters not found"**
→ `pip install langchain-mcp-adapters`

**"API key error"**
→ Set GOOGLE_API_KEY in .env file

## 📝 License

MIT