"""
tests/test_tools.py

Pytest tests for each FitFindr tool, covering happy paths and failure modes.
Run with: pytest tests/
"""

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    """Impossible query — should return [] without raising."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=30)
    assert all(item["price"] <= 30 for item in results)

def test_search_size_filter():
    results = search_listings("top", size="M", max_price=None)
    for item in results:
        assert "m" in item["size"].lower()


# ── suggest_outfit ────────────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe():
    results = search_listings("graphic tee", size=None, max_price=50)
    assert len(results) > 0
    suggestion = suggest_outfit(results[0], get_example_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 10

def test_suggest_outfit_empty_wardrobe():
    """Empty wardrobe should return general advice, not crash."""
    results = search_listings("cardigan", size=None, max_price=50)
    assert len(results) > 0
    suggestion = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 10


# ── create_fit_card ───────────────────────────────────────────────────────────

def test_create_fit_card_returns_string():
    results = search_listings("graphic tee", size=None, max_price=50)
    assert len(results) > 0
    item = results[0]
    outfit = suggest_outfit(item, get_example_wardrobe())
    card = create_fit_card(outfit, item)
    assert isinstance(card, str)
    assert len(card) > 10

def test_create_fit_card_empty_outfit():
    """Empty outfit string should return an error message, not raise."""
    results = search_listings("jeans", size=None, max_price=None)
    assert len(results) > 0
    card = create_fit_card("", results[0])
    assert isinstance(card, str)
    assert "couldn't" in card.lower() or "empty" in card.lower()