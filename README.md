# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory

| Tool | Inputs | Return value | Purpose |
|------|--------|-------------|---------|
| `search_listings` | `description` (str), `size` (str \| None), `max_price` (float \| None) | `list[dict]` — matching listing dicts sorted by relevance score, or `[]` if no matches | Searches the mock listings dataset for secondhand items matching the user's keywords, with optional size and price filters |
| `suggest_outfit` | `new_item` (dict), `wardrobe` (dict) | `str` — 1–2 outfit combinations using wardrobe pieces, or general styling advice if wardrobe is empty | Calls the LLM to suggest complete outfits pairing the new item with pieces the user already owns |
| `create_fit_card` | `outfit` (str), `new_item` (dict) | `str` — a 2–4 sentence Instagram/TikTok-style caption | Calls the LLM to generate a casual, shareable caption capturing the outfit vibe and mentioning the item name, price, and platform |

---

## Interaction Walkthrough

**User query:** "looking for a vintage graphic tee under $30"

**Step 1 — Tool called:**
- Tool: `search_listings`
- Input: `description="vintage graphic tee"`, `size=None`, `max_price=30.0`
- Why this tool: The agent always starts here — it parses the user's query with regex to extract keywords, size, and price, then searches the dataset to find real listings before doing anything else.
- Output: A list of matching listings sorted by keyword overlap score. Top result: `"Y2K Baby Tee — Butterfly Print"` ($18.00, depop, size S/M, tags: y2k, vintage, graphic tee).

**Step 2 — Tool called:**
- Tool: `suggest_outfit`
- Input: `new_item=<Y2K Baby Tee listing dict>`, `wardrobe=<example wardrobe with 10 items>`
- Why this tool: A listing was found, so the agent proceeds to outfit suggestions. The top result from Step 1 is passed in directly from `session["selected_item"]` — the user doesn't re-enter anything.
- Output: "Pair the Y2K Baby Tee with the baggy straight-leg jeans and chunky white sneakers for a casual, retro-inspired look. Tuck the tee into the jeans to create a defined waistline. For a different vibe, combine the baby tee with the wide-leg khaki trousers and black combat boots — layer the vintage black denim jacket over the tee to add some edge."

**Step 3 — Tool called:**
- Tool: `create_fit_card`
- Input: `outfit=<suggestion string from Step 2>`, `new_item=<Y2K Baby Tee listing dict>`
- Why this tool: An outfit suggestion exists, so the agent generates a shareable caption. The outfit string flows directly from `session["outfit_suggestion"]` — no re-entry needed.
- Output: "i just scored this adorable y2k baby tee — butterfly print on depop for $18 and i'm obsessed 🥰 been wearing it with my baggy straight-leg jeans and chunky white sneakers for a super casual retro vibe, but it also goes crazy with wide-leg khakis and combat boots if you want something more eclectic."

**Final output to user:**
The Gradio interface populates three panels simultaneously:
- **Top listing found:** Full listing details (title, price, condition, size, platform, colors, style tags, description)
- **Outfit idea:** The LLM's specific outfit combinations naming exact wardrobe pieces
- **Your fit card:** The casual 2–4 sentence caption ready to copy and post

---

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | Returns `[]` — no listings match the description, size, and price filters | Sets `session["error"]` to a specific message explaining which filters were applied and suggesting what to change (e.g. "No listings found for 'designer ballgown' (size XXS, under $5). Try removing the size filter, raising your max price, or broadening your description."). Returns the session immediately — `suggest_outfit` and `create_fit_card` are never called with empty input. |
| `suggest_outfit` | Wardrobe is empty (`wardrobe["items"] == []`) | Detects the empty wardrobe and switches to a general styling prompt instead of a wardrobe-specific one. The LLM returns general advice on what pairs well with the item and what vibe it suits. Returns a non-empty string — never crashes or returns `""`. |
| `create_fit_card` | `outfit` argument is empty or whitespace-only | Guards at the top of the function before calling the LLM. Immediately returns the error string: "Couldn't generate a fit card — outfit suggestion was empty. Please try the full flow again." No exception is raised. |

---

## Spec Reflection

**One way planning.md helped during implementation:**

Writing out the exact conditional logic for the planning loop in planning.md before touching agent.py made the implementation straightforward. Because the spec described each branch precisely — "if results == [], set session['error'] and return early; do NOT proceed to suggest_outfit" — there was no ambiguity when writing the code. It also made it easy to verify correctness: the CLI test in agent.py directly tests the no-results path, and the expected behavior was already written down to check against.

**One divergence from your spec, and why:**

The spec described stripping size and price phrases from the query to produce a clean description, but the initial regex left the word "size" behind in the description string (e.g., "designer ballgown size" instead of "designer ballgown"). This happened because the size pattern only matched the size value (like "XXS") and not the word "size" before it. The fix was adding "size" to the filler words regex that gets stripped after parsing — a small change, but one that wasn't anticipated in the original spec because the edge case only appeared when actually running the no-results test.

---

## AI Usage

**Instance 1 — Implementing the three tools in tools.py:**
I gave Claude the Tool 1, 2, and 3 spec blocks from planning.md (inputs, return values, failure modes) along with the listings.json schema and wardrobe_schema.json. I asked it to implement each function while preserving all original docstrings and TODO comments from the starter code. I verified that search_listings filtered by all three parameters and scored by keyword overlap across title, description, and style_tags; that suggest_outfit branched correctly on empty wardrobe; and that create_fit_card guarded against an empty outfit string before calling the LLM. I then ran pytest tests/ to confirm all 8 tests passed before moving on.

**Instance 2 — Implementing the planning loop in agent.py:**
I gave Claude the Architecture diagram and Planning Loop + State Management sections from planning.md, along with the original agent.py starter code, and asked it to implement run_agent() without removing any existing comments or structure. I verified that the generated code branched on empty search_results and returned early, that state flowed through the session dict without any hardcoded values between steps, and that suggest_outfit was never called when search returned an empty list. I tested both paths using the CLI test already in agent.py and confirmed the no-results path produced a helpful error message rather than crashing.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.