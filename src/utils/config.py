"""Configuration for the trading bot"""
import json
from pathlib import Path
from typing import Set, Dict, List

def load_tradeables() -> Set[str]:
    """Load all tradeable items from tradeables.json"""
    tradeable_file = Path("data/tradeables.json")
    if not tradeable_file.exists():
        print("Warning: tradeables.json not found")
        return set()
        
    with open(tradeable_file) as f:
        data = json.load(f)
        
    tradeables = set()
    
    def process_items(items):
        """Process items recursively"""
        if isinstance(items, list):
            tradeables.update(items)
        elif isinstance(items, dict):
            for value in items.values():
                process_items(value)
    
    # Process each category
    for category, items in data.items():
        process_items(items)
    
    return tradeables

# Load all tradeable items
TRADEABLE_ITEMS = load_tradeables()

# Common currency items that are frequently traded
COMMON_CURRENCIES = {
    "chaos_orb",
    "divine_orb",
    "exalted_orb",
    "vaal_orb",
    "orb_of_alchemy",
    "orb_of_annulment",
}

# Weight for random selection (common currencies are more likely to be selected)
CURRENCY_WEIGHTS = {
    item: 5.0 if item in COMMON_CURRENCIES else 1.0
    for item in TRADEABLE_ITEMS
}

# Currency pairs available for trading
CURRENCY_PAIRS = {
    "chaos": "Chaos Orb",
    "divine": "Divine Orb",
    "exalted": "Exalted Orb",
    "ancient": "Ancient Orb",
    "annul": "Orb of Annulment",
    "awakened": "Awakened Sextant",
    "blessing": "Blessing",
    "delirium": "Delirium Orb",
    "essence": "Essence",
    "fossil": "Fossil",
    "resonator": "Resonator",
    "scarab": "Scarab",
    "vaal": "Vaal Orb",
    "alchemy": "Orb of Alchemy",
    "alteration": "Orb of Alteration",
    "chromatic": "Chromatic Orb",
    "fusing": "Orb of Fusing",
    "jeweller": "Jeweller's Orb",
    "regret": "Orb of Regret",
    "scouring": "Orb of Scouring"
} 