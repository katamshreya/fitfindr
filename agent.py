"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1: Initialize the session with _new_session()
    session = _new_session(query, wardrobe)

    # Step 2: Parse the user's query using regex to extract description, size,
    # and max_price. Store the result in session["parsed"].
    size = None
    max_price = None

    size_match = re.search(r'\b(XXS|XS|S/M|M/L|L/XL|XL/XXL|XXS|XS|S|M|L|XL|XXL)\b', query, re.IGNORECASE)
    if size_match:
        size = size_match.group(1).upper()

    price_match = re.search(r'(?:under|less than|max|up to|below)\s*\$?\s*(\d+(?:\.\d+)?)', query, re.IGNORECASE)
    if price_match:
        max_price = float(price_match.group(1))

    # Strip size/price phrases to get the core description
    description = query
    if size_match:
        description = description[:size_match.start()] + description[size_match.end():]
    if price_match:
        price_phrase = re.search(
            r'(?:under|less than|max|up to|below)\s*\$?\s*\d+(?:\.\d+)?',
            description, re.IGNORECASE
        )
        if price_phrase:
            description = description[:price_phrase.start()] + description[price_phrase.end():]

    filler = r'\b(i\'m looking for|looking for|i want|i need|find me|size|a|an|some|the|,)\b'
    description = re.sub(filler, ' ', description, flags=re.IGNORECASE)
    description = ' '.join(description.split())

    session["parsed"] = {
        "description": description or query,
        "size": size,
        "max_price": max_price,
    }

    # Step 3: Call search_listings() with the parsed parameters.
    # Store results in session["search_results"].
    # If no results: set session["error"] to a helpful message and return early.
    session["search_results"] = search_listings(
        session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )

    if not session["search_results"]:
        filter_parts = []
        if size:
            filter_parts.append(f"size {size}")
        if max_price is not None:
            filter_parts.append(f"under ${max_price:.0f}")
        filter_str = f" ({', '.join(filter_parts)})" if filter_parts else ""

        session["error"] = (
            f"No listings found for '{session['parsed']['description']}'{filter_str}. "
            f"Try removing the size filter, raising your max price, or broadening your description."
        )
        return session  # Do NOT proceed to suggest_outfit with empty input

    # Step 4: Select the item to use (top result). Store it in session["selected_item"].
    session["selected_item"] = session["search_results"][0]

    # Step 5: Call suggest_outfit() with the selected item and wardrobe.
    # Store the result in session["outfit_suggestion"].
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"],
        session["wardrobe"],
    )

    # Step 6: Call create_fit_card() with the outfit suggestion and selected item.
    # Store the result in session["fit_card"].
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"],
        session["selected_item"],
    )

    # Step 7: Return the session.
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")