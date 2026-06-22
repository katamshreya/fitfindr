# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Searches the mock listings dataset for secondhand items that match a keyword description, with optional filters for size and max price. Returns a ranked list of matching listings sorted by relevance (keyword overlap score), or an empty list if nothing matches.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): Keywords describing the item the user wants (e.g., "vintage graphic tee"). Used to score each listing by overlap against its title, description, and style_tags fields.
- `size` (str): Size string to filter by (e.g., "M"). Matched as a case-insensitive substring so "M" matches "S/M". Pass None to skip size filtering.
- `max_price` (float): Maximum price inclusive (e.g., 30.0). Pass None to skip price filtering.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list[dict] of matching listing dicts, sorted by relevance score (highest first). Each dict contains: id (str), title (str), description (str), category (str), style_tags (list[str]), size (str), condition (str), price (float), colors (list[str]), brand (str | None), platform (str). Returns [] (empty list) if no listings match it never raises an exception.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
The agent checks if results == []. If so, it sets session["error"] to a specific message like: "No listings found for 'vintage graphic tee' (size M, under $30). Try removing the size filter, raising your max price, or broadening your description." The agent then returns the session early — it does NOT call suggest_outfit with empty input.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given a thrifted item the user is considering and their existing wardrobe, calls the LLM to suggest 1–2 complete outfit combinations. If the wardrobe is empty, returns general styling advice for the item instead of specific combinations.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A listing dict (the item from search_listings the user is considering buying). Used to give the LLM context on the item's style, colors, and category.
- `wardrobe` (dict): A wardrobe dict with an items key containing a list of wardrobe item dicts. Each wardrobe item has: id, name, category, colors (list), style_tags (list), notes (str | None). May be empty — must be handled gracefully.

**What it returns:**
<!-- Describe the return value -->
A non-empty str with outfit suggestion(s). If wardrobe has items: specific combinations naming exact wardrobe pieces. If wardrobe is empty: general advice on what kinds of pieces pair well, what vibe the item suits, and one styling tip. Never returns an empty string.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If wardrobe["items"] is empty, the function still calls the LLM with a general styling prompt — it does not crash or return "". If the LLM call itself fails (network error, etc.), the function catches the exception and returns a fallback string: "Couldn't generate suggestions right now. This item would pair well with straight-leg jeans and clean sneakers as a starting point."

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Generates a 2–4 sentence Instagram/TikTok-style caption for the thrifted find and outfit — the kind of thing someone would actually post as an OOTD. Sounds casual and authentic, mentions the item name, price, and platform once each, and varies each time it's called.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string returned by suggest_outfit(). Used to capture the vibe and specific pieces in the caption.
- `new_item` (dict): The listing dict for the thrifted item. Used to pull the title, price, and platform for natural mention in the caption.

**What it returns:**
<!-- Describe the return value -->
A str of 2–4 sentences usable as a social media caption. Casual tone, lowercase is fine, 1–2 emojis max, no hashtags. Sounds different each time for different inputs (LLM temperature ~1.1). Never raises an exception.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If outfit is empty or whitespace-only, the function immediately returns the error string: "Couldn't generate a fit card — outfit suggestion was empty. Please try the full flow again." without calling the LLM. If the LLM call fails, catches the exception and returns a short fallback caption string.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
After receiving the user's query, the agent runs the following conditional logic:
 
1. Parse the query using regex to extract `description`, `size` (or None), and `max_price` (or None). Store in `session["parsed"]`.
2. Call `search_listings(description, size, max_price)`. Store results in `session["search_results"]`.
   - **IF** `results == []`: set `session["error"]` to a helpful message describing what filters were applied and what the user can try. **Return session immediately.** Do NOT proceed.
   - **IF** `results` is non-empty: continue.
3. Set `session["selected_item"] = results[0]` (top relevance-ranked result).
4. Call `suggest_outfit(session["selected_item"], session["wardrobe"])`. Store result in `session["outfit_suggestion"]`.
5. Call `create_fit_card(session["outfit_suggestion"], session["selected_item"])`. Store result in `session["fit_card"]`.
6. Return the completed session.
The agent does NOT call all tools unconditionally. Steps 4 and 5 only execute if Step 2 returned results. The loop terminates early (Step 2) if search fails, and the downstream tools are never called with empty input.
---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
All state lives in a single `session` dict initialized at the start of `run_agent()`. No global variables. Each tool writes its output into a named key, and the next tool reads from that key:
 
| Key | Written by | Read by |
|-----|-----------|---------|
| `session["query"]` | _new_session() at start | query parser |
| `session["parsed"]` | query parser (Step 1) | search_listings call |
| `session["search_results"]` | search_listings (Step 2) | item selection (Step 3) |
| `session["selected_item"]` | Step 3 | suggest_outfit, create_fit_card |
| `session["wardrobe"]` | _new_session() at start | suggest_outfit |
| `session["outfit_suggestion"]` | suggest_outfit (Step 4) | create_fit_card |
| `session["fit_card"]` | create_fit_card (Step 5) | returned to app.py |
| `session["error"]` | early exit (Step 2) | checked by app.py before display |
 
The session dict is passed through every step in the same `run_agent()` call. `app.py` receives the completed session and maps keys to the three output panels.
---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets session["error"] = "No listings found for '[description]' (size [X], under $[Y]). Try removing the size filter, raising your max price, or broadening your description." Returns session early — suggest_outfit and create_fit_card are never called. |
| suggest_outfit | Wardrobe is empty | Calls LLM with a general styling prompt instead of wardrobe-specific one. Returns general advice as a non-empty string. Does not crash or return "". |
| create_fit_card | Outfit input is missing or incomplete | If outfit is empty/whitespace, immediately returns "Couldn't generate a fit card — outfit suggestion was empty. Please try the full flow again." without calling the LLM. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     Use ASCII art or a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html).
     Do NOT embed an image — graders need to read your diagram directly in the file;
     an embedded image or screenshot cannot be evaluated.
     You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->
```
User query (natural language)
    │
    ▼
run_agent(query, wardrobe)
    │
    ▼
Step 1: Parse query (regex)
    │ → session["parsed"] = {description, size, max_price}
    ▼
Step 2: search_listings(description, size, max_price)
    │ → session["search_results"] = [...]
    │
    ├─ results == [] ──► session["error"] = "No listings found..."
    │                    RETURN session (early exit) ──────────────► user sees error
    │
    │ results non-empty
    ▼
Step 3: session["selected_item"] = results[0]
    │
    ▼
Step 4: suggest_outfit(selected_item, wardrobe)
    │ → session["outfit_suggestion"] = "..."
    │
    │   [if wardrobe empty: LLM gives general advice instead]
    │
    ▼
Step 5: create_fit_card(outfit_suggestion, selected_item)
    │ → session["fit_card"] = "..."
    │
    │   [if outfit empty: returns error string, skips LLM]
    │
    ▼
RETURN session
    │
    ▼
app.py maps session keys → 3 output panels
```
---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
For `search_listings`: I gave Claude the Tool 1 spec above (inputs, return value, failure mode) and the listings.json schema, and asked it to implement the function using load_listings() from the data loader. I verified the output filters by all three parameters, scores by keyword overlap across title/description/style_tags, and returns [] on no match without raising. Tested with 3 queries: "vintage graphic tee under $30", "designer ballgown size XXS under $5" (expect []), and "jacket size M".
 
For `suggest_outfit`: I gave Claude the Tool 2 spec block and wardrobe_schema.json, and asked it to implement using Groq llama-3.3-70b-versatile. I verified it branches on empty wardrobe, returns a non-empty string in both branches, and catches LLM exceptions. Tested with get_example_wardrobe() and get_empty_wardrobe().
 
For `create_fit_card`: I gave Claude the Tool 3 spec block and asked it to implement with temperature ~1.1 for variation. I verified it guards against empty outfit before calling the LLM, and ran it 3 times on the same input to confirm outputs differed.

**Milestone 4 — Planning loop and state management:**
For `run_agent`: I gave Claude the Architecture diagram and Planning Loop + State Management sections above, and asked it to implement run_agent() following the numbered steps. I verified: (1) it branches on empty search_results and returns early, (2) state flows through the session dict without hardcoded values, (3) suggest_outfit is never called when search returns []. Tested the no-results path explicitly with "designer ballgown size XXS under $5".
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The agent parses the query using regex. It extracts: description = "vintage graphic tee", size = None (no size mentioned), max_price = 30.0. These are stored in session["parsed"]. The wardrobe provided is the example_wardrobe (baggy jeans, chunky sneakers, etc.).

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
`search_listings("vintage graphic tee", size=None, max_price=30.0)` is called. The function loads all listings, filters to price ≤ $30, then scores each remaining listing by keyword overlap with "vintage graphic tee". Listings with score 0 are dropped. Results are sorted by score. Returns: [lst_006 "Graphic Tee — 2003 Tour Bootleg Style" ($24), lst_033 "Vintage Band Tee — Faded Grey" ($19), lst_002 "Y2K Baby Tee — Butterfly Print" ($18), ...]. Results are stored in session["search_results"]. Results are non-empty → continue.

**Step 3:**
<!-- Continue until the full interaction is complete -->
Agent sets session["selected_item"] = results[0] = lst_006 ("Graphic Tee — 2003 Tour Bootleg Style", $24, depop, black, size L, style_tags: graphic tee/vintage/grunge/streetwear).

**Step 4:**
`suggest_outfit(lst_006, example_wardrobe)` is called. The wardrobe has items (not empty), so the LLM receives a prompt listing the wardrobe pieces and asks for specific outfit combinations using the new item. LLM returns something like: "Pair this boxy black graphic tee with your baggy dark-wash jeans and chunky white sneakers for a classic 90s streetwear look — tuck the front corner in slightly for shape. For a grungier vibe, swap the sneakers for your black combat boots and let the tee hang loose." Stored in session["outfit_suggestion"].
 
**Step 5:**
`create_fit_card(outfit_suggestion, lst_006)` is called. Outfit string is non-empty → LLM is called with item details (title, $24, depop) and outfit description. Temperature is 1.1 for variation. LLM returns: "thrifted this 2003 bootleg tee off depop for $24 and it was literally made for baggy jeans 🖤 boxy fit, slightly tucked front — giving exactly the 90s streetwear energy i needed." Stored in session["fit_card"].

**Final output to user:**
<!-- What does the user actually see at the end? -->
The app.py maps the session to three panels:
- **Top Listing Found:** "Graphic Tee — 2003 Tour Bootleg Style — $24.00, Condition: Good, Size: L, Platform: Depop, Colors: Black, Style: graphic tee, vintage, grunge, streetwear. [description text]"
- **Outfit Suggestion:** The LLM's specific outfit combinations using named wardrobe pieces.
- **Fit Card Caption:** The casual 2–4 sentence Instagram-style caption.
