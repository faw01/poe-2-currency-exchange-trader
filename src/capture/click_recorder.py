import json
import pyautogui
import time
from pathlib import Path
from typing import List, Dict, Literal, Set, Optional
import pytesseract
from PIL import Image
import io

# Valid sequence types
SequenceType = Literal["select", "amount", "trade", "market"]
SEQUENCE_TYPES = {
    "select": "Positions for selecting the currency/item (e.g., clicking currency tab, clicking item)",
    "amount": "Positions for entering amount (e.g., clicking amount field)",
    "trade": "Position for clicking the trade button",
    "market": "Position for checking market prices (moves to position, holds cmd, captures text)"
}

# Fixed position prefixes
FIXED_PREFIXES = {
    "i_want": [{"x": 700, "y": 240}],  # Fixed position for "I want" tab
    "i_have": [{"x": 1200, "y": 240}]  # Fixed position for "I have" tab
}

# Category positions for i_want tab
I_WANT_CATEGORY_POSITIONS = {
    "currency": {"x": 530, "y": 250},    # 200 + 30
    "delirium": {"x": 530, "y": 280},    # 250 + 30
    "breach": {"x": 530, "y": 330},      # 280 + 30
    "fragments": {"x": 530, "y": 370},   # 320 + 30
    "expedition": {"x": 530, "y": 410},  # 360 + 30
    "essences": {"x": 530, "y": 450},    # 400 + 30
    "runes": {"x": 530, "y": 490},       # 450 + 30
    "omens": {"x": 530, "y": 530},       # 480 + 30
    "soul_cores": {"x": 530, "y": 570}   # 530 + 30
}

# Category positions for i_have tab (same x, y+50)
I_HAVE_CATEGORY_POSITIONS = {
    category: {"x": pos["x"], "y": pos["y"] + 40}
    for category, pos in I_WANT_CATEGORY_POSITIONS.items()
}

# Fixed category order
CATEGORY_ORDER = [
    "currency",
    "delirium",
    "breach",
    "fragments",
    "expedition",
    "essences",
    "runes",
    "omens",
    "soul_cores"
]

def load_item_categories() -> Dict[str, str]:
    """Load item to category mappings from tradeables.json"""
    tradeable_file = Path("data/tradeables.json")
    if not tradeable_file.exists():
        print("Warning: tradeables.json not found")
        return {}
        
    with open(tradeable_file) as f:
        data = json.load(f)
        
    item_categories = {}
    
    # Process each top-level category
    for category, items in data.items():
        if isinstance(items, list):
            # Direct list of items
            for item in items:
                item_categories[item] = category
        elif isinstance(items, dict):
            # Nested subcategories
            for subcategory, subitems in items.items():
                if isinstance(subitems, list):
                    for item in subitems:
                        # Store with top-level category
                        item_categories[item] = category
    
    return item_categories

ITEM_CATEGORIES = load_item_categories()

def get_category_for_item(item_name: str) -> str:
    """Get the category for an item based on its name"""
    # Remove i_want_ or i_have_ prefix if present
    clean_name = item_name
    if clean_name.startswith("i_want_"):
        clean_name = clean_name[7:]
    elif clean_name.startswith("i_have_"):
        clean_name = clean_name[7:]

    # Try direct lookup
    if clean_name in ITEM_CATEGORIES:
        return ITEM_CATEGORIES[clean_name]

    # If not found, try to match by category name
    for category in CATEGORY_ORDER:
        if category in clean_name:
            return category

    # Default to currency if no match found
    print(f"Warning: No category found for {clean_name}, defaulting to currency")
    return "currency"

def get_clicks_for_category(category: str, is_want: bool = True) -> List[Dict[str, int]]:
    """Get the sequence of clicks needed for a category"""
    positions = I_WANT_CATEGORY_POSITIONS if is_want else I_HAVE_CATEGORY_POSITIONS
    if category not in positions:
        return []
    return [positions[category]]

def load_tradeables() -> Set[str]:
    """Load all tradeable items from tradeables.json"""
    tradeable_file = Path("data/tradeables.json")
    if not tradeable_file.exists():
        print("Warning: tradeables.json not found")
        return set()
        
    with open(tradeable_file) as f:
        data = json.load(f)
        
    tradeables = set()
    
    # Process each category
    for category, items in data.items():
        if category == "popular":  # Skip popular as it's a special category
            continue
            
        if isinstance(items, dict):  # Handle nested categories
            for subcategory in items.values():
                if isinstance(subcategory, list):
                    tradeables.update(subcategory)
        elif isinstance(items, list):
            if all(isinstance(item, dict) for item in items):  # Handle items with metadata
                tradeables.update(item["name"] for item in items)
            else:
                tradeables.update(items)
    
    return tradeables

def capture_market_info(x: int, y: int, item_name: str = "", region: Dict[str, int] = None) -> str:
    """Capture and process market information from screen"""
    # Use provided region or default to centered region
    if region:
        screenshot_region = (
            region["x1"],
            region["y1"],
            region["x2"] - region["x1"],
            region["y2"] - region["y1"]
        )
    else:
        width = 400
        height = 300
        screenshot_region = (x - width//2, y - height//2, width, height)
    
    # Create screenshots directory if it doesn't exist
    screenshot_dir = Path("data/market_screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Capture the screen region
    screenshot = pyautogui.screenshot(region=screenshot_region)
    
    # Save the screenshot with timestamp and item name
    filename = f"{timestamp}_{item_name}_market.png" if item_name else f"{timestamp}_market.png"
    screenshot.save(screenshot_dir / filename)
    print(f"Screenshot saved as: {filename}")
    
    # Use OCR to extract text
    text = pytesseract.image_to_string(screenshot)
    return text

class ClickRecorder:
    def __init__(self):
        self.sequences: Dict[str, Dict[str, List[Dict[str, int]]]] = {}
        self.data_file = Path("data/click_sequences.json")
        self.prefix_file = Path("data/prefix_sequences.json")
        pyautogui.PAUSE = 0.1  # Add small delay between actions
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        self.load_sequences()
        self.load_prefixes()

    def load_sequences(self):
        """Load saved click sequences"""
        if self.data_file.exists():
            with open(self.data_file) as f:
                self.sequences = json.load(f)

    def save_sequences(self):
        """Save click sequences to file"""
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(self.sequences, f, indent=2)

    def load_prefixes(self):
        """Load prefix sequences"""
        self.prefixes = {}
        if self.prefix_file.exists():
            with open(self.prefix_file) as f:
                self.prefixes = json.load(f)

    def save_prefixes(self):
        """Save prefix sequences"""
        self.prefix_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.prefix_file, 'w') as f:
            json.dump(self.prefixes, f, indent=2)

    def delete_all_sequences(self):
        """Delete all recorded sequences"""
        self.sequences = {}
        self.save_sequences()
        print("All sequences deleted")
        
    def delete_sequence(self, item_name: str, sequence_type: str = None):
        """Delete a specific sequence or all sequences for an item"""
        if item_name not in self.sequences:
            print(f"No sequences found for {item_name}")
            return False
            
        if sequence_type:
            if sequence_type in self.sequences[item_name]:
                del self.sequences[item_name][sequence_type]
                if not self.sequences[item_name]:  # If no sequences left for item
                    del self.sequences[item_name]
                self.save_sequences()
                print(f"Deleted {sequence_type} sequence for {item_name}")
                return True
            else:
                print(f"No {sequence_type} sequence found for {item_name}")
                return False
        else:
            del self.sequences[item_name]
            self.save_sequences()
            print(f"Deleted all sequences for {item_name}")
            return True

    def record_prefix(self, prefix_name: str):
        """Record a prefix sequence of clicks"""
        print(f"\nRecording prefix sequence: {prefix_name}")
        print("Record the common clicks that should happen before item-specific clicks")
        print("\nCommands:")
        print("Enter - Record current mouse position")
        print("q - Finish recording")
        print("Move mouse to top-left corner to abort")
        print("\nPosition your mouse and press Enter to record each position...")
        
        clicks = []
        
        try:
            while True:
                command = input()
                
                if command.lower() == 'q':
                    break
                    
                pos = pyautogui.position()
                clicks.append({"x": pos.x, "y": pos.y})
                print(f"Recorded position at ({pos.x}, {pos.y})")
                
        except pyautogui.FailSafeException:
            print("\nRecording aborted (mouse moved to corner)")
            return False

        if not clicks:
            print("No positions recorded")
            return False

        self.prefixes[prefix_name] = clicks
        self.save_prefixes()
        
        print(f"\nRecorded prefix with {len(clicks)} positions")
        return True

    def record_sequence(self, item_name: str, sequence_type: str = "select"):
        """Record a sequence of clicks for an item"""
        if sequence_type not in SEQUENCE_TYPES:
            print(f"Invalid sequence type. Valid types are: {', '.join(SEQUENCE_TYPES.keys())}")
            return False
            
        print(f"\nRecording clicks for {item_name} ({sequence_type})")
        print(f"Purpose: {SEQUENCE_TYPES[sequence_type]}")
        
        # For market sequences, get capture region first
        capture_region = None
        if sequence_type == "market":
            print("\nSelect the region to capture:")
            print("1. Move to top-left corner and press Enter")
            print("2. Move to bottom-right corner and press Enter")
            print("Press 'q' to cancel")
            
            try:
                # Get top-left corner
                while True:
                    command = input()
                    if command.lower() == 'q':
                        return False
                    pos1 = pyautogui.position()
                    print(f"Top-left corner: ({pos1.x}, {pos1.y})")
                    break
                
                print("\nNow move to bottom-right corner and press Enter")
                # Get bottom-right corner
                while True:
                    command = input()
                    if command.lower() == 'q':
                        return False
                    pos2 = pyautogui.position()
                    print(f"Bottom-right corner: ({pos2.x}, {pos2.y})")
                    break
                
                capture_region = {
                    "x1": min(pos1.x, pos2.x),
                    "y1": min(pos1.y, pos2.y),
                    "x2": max(pos1.x, pos2.x),
                    "y2": max(pos1.y, pos2.y)
                }
                print(f"\nCapture region: {capture_region['x2'] - capture_region['x1']}x{capture_region['y2'] - capture_region['y1']} pixels")
            
            except pyautogui.FailSafeException:
                print("\nRecording aborted (mouse moved to corner)")
                return False
            
            print("\nPosition your mouse over the tradeable and press Enter")
            print("Press 'q' to cancel")
        else:
            print("\nCommands:")
            print("Enter - Record current mouse position")
            print("q - Finish recording")
            print("Move mouse to top-left corner to abort")
            print("\nPosition your mouse and press Enter to record each position...")
        
        clicks = []
        expected_positions = 1 if sequence_type == "market" else 0  # 1 position for market (just tradeable), unlimited for others
        
        try:
            while True:
                command = input()
                
                if command.lower() == 'q':
                    break
                    
                pos = pyautogui.position()
                click_data = {"x": pos.x, "y": pos.y}
                
                if sequence_type == "market":
                    click_data["region"] = capture_region
                
                clicks.append(click_data)
                print(f"Position recorded at ({pos.x}, {pos.y})")
                
                if expected_positions > 0 and len(clicks) >= expected_positions:
                    break
                
        except pyautogui.FailSafeException:
            print("\nRecording aborted (mouse moved to corner)")
            return False

        if not clicks:
            print("No positions recorded")
            return False

        if item_name not in self.sequences:
            self.sequences[item_name] = {}
        self.sequences[item_name][sequence_type] = clicks
        self.save_sequences()
        
        print(f"\nRecorded {len(clicks)} positions")
        return True

    def play_sequence(self, item_name: str, sequence_type: str = "select", current_i_want: Optional[str] = None, amount: Optional[str] = None):
        """Play back a recorded sequence"""
        if sequence_type not in SEQUENCE_TYPES:
            print(f"Invalid sequence type. Valid types are: {', '.join(SEQUENCE_TYPES.keys())}")
            return False
            
        if item_name not in self.sequences or sequence_type not in self.sequences[item_name]:
            print(f"No {sequence_type} sequence found for {item_name}")
            return False

        sequence = self.sequences[item_name][sequence_type]
        
        # For amount sequences, use the provided amount
        if sequence_type == "amount":
            if amount is None:
                print("Error: amount parameter is required for amount sequences")
                return False
            
            print("\nSwitch to POE window...")
            time.sleep(0.5)  # Give time to switch windows
            
            for click in sequence:
                # 1. Click the input field
                pyautogui.moveTo(click["x"], click["y"])
                time.sleep(0.1)  # Delay before click
                pyautogui.click()
                time.sleep(0.1)  # Delay after click
                
                # 2. Select all text (Command+A)
                pyautogui.hotkey('command', 'a')
                time.sleep(0.1)  # Delay after select all
                
                # 3. Press backspace to delete
                pyautogui.press('backspace')
                time.sleep(0.1)  # Delay after delete
                
                # 4. Type the new amount
                pyautogui.write(str(amount))
                time.sleep(0.1)  # Delay after typing
        elif sequence_type == "market":
            print("\nSwitch to POE window...")
            time.sleep(0.5)  # Give time to switch windows
            
            # Move to position and capture market info
            tradeable_click = sequence[0]  # Only one position recorded - the tradeable
            print(f"Moving to position ({tradeable_click['x']}, {tradeable_click['y']})")
            pyautogui.moveTo(tradeable_click["x"], tradeable_click["y"])
            time.sleep(0.1)  # Delay before capture
            
            # Hold command key and capture
            for _ in range(3):  # Try up to 3 times to ensure key is pressed
                pyautogui.keyDown('command')
                time.sleep(0.1)  # Small delay to ensure key is registered
            
            time.sleep(0.5)  # Wait for market info to appear
            
            # Capture and analyze market info
            market_text = capture_market_info(
                tradeable_click["x"], 
                tradeable_click["y"], 
                item_name, 
                tradeable_click.get("region", None)
            )
            
            # Release command key (multiple times to ensure it's released)
            for _ in range(3):
                pyautogui.keyUp('command')
                time.sleep(0.1)
        elif sequence_type == "trade":
            print("\nSwitch to POE window...")
            time.sleep(0.5)  # Give time to switch windows
            
            # Simply move to position and click
            for click in sequence:
                print(f"Clicking trade button at ({click['x']}, {click['y']})")
                pyautogui.moveTo(click["x"], click["y"])
                time.sleep(0.1)  # Delay before click
                pyautogui.click()
                time.sleep(0.1)  # Delay after click
        else:
            print("\nSwitch to POE window...")
            time.sleep(0.5)  # Give time to switch windows
            
            # Determine if this is i_want or i_have
            is_want = item_name.startswith("i_want_")
            clean_name = item_name[7:]  # Remove i_want_ or i_have_ prefix
            
            # For i_want sequences, check if we need to change the tab and category
            if is_want:
                if current_i_want is None or current_i_want != clean_name:
                    # Click the i_want tab
                    tab_pos = FIXED_PREFIXES["i_want"][0]
                    print(f"Clicking i_want tab at ({tab_pos['x']}, {tab_pos['y']})")
                    pyautogui.moveTo(tab_pos["x"], tab_pos["y"])
                    time.sleep(0.1)  # Delay before click
                    pyautogui.click()
                    time.sleep(0.1)  # Delay after click
                    
                    # Click the category
                    category = get_category_for_item(clean_name)
                    category_pos = I_WANT_CATEGORY_POSITIONS[category]
                    print(f"Clicking {category} category at ({category_pos['x']}, {category_pos['y']})")
                    pyautogui.moveTo(category_pos["x"], category_pos["y"])
                    time.sleep(0.1)  # Delay before click
                    pyautogui.click()
                    time.sleep(0.1)  # Delay after click
                else:
                    print(f"Keeping current i_want {clean_name}...")
            else:
                # Always click i_have tab and category
                tab_pos = FIXED_PREFIXES["i_have"][0]
                print(f"Clicking i_have tab at ({tab_pos['x']}, {tab_pos['y']})")
                pyautogui.moveTo(tab_pos["x"], tab_pos["y"])
                time.sleep(0.1)  # Delay before click
                pyautogui.click()
                time.sleep(0.1)  # Delay after click
                
                # Click the category
                category = get_category_for_item(clean_name)
                category_pos = I_HAVE_CATEGORY_POSITIONS[category]  # Use I_HAVE_CATEGORY_POSITIONS here
                print(f"Clicking {category} category at ({category_pos['x']}, {category_pos['y']})")
                pyautogui.moveTo(category_pos["x"], category_pos["y"])
                time.sleep(0.1)  # Delay before click
                pyautogui.click()
                time.sleep(0.1)  # Delay after click
            
            # Click the item position
            for click in sequence:
                print(f"Clicking item at ({click['x']}, {click['y']})")
                pyautogui.moveTo(click["x"], click["y"])
                time.sleep(0.1)  # Delay before click
                pyautogui.click()
                time.sleep(0.1)  # Delay after click
        
        return True

def test_category_position(category: str, is_want: bool = True):
    """Test clicking a category position"""
    positions = I_WANT_CATEGORY_POSITIONS if is_want else I_HAVE_CATEGORY_POSITIONS
    if category not in positions:
        print(f"Category {category} not found!")
        return False
        
    pos = positions[category]
    side = "i_want" if is_want else "i_have"
    print(f"Clicking {side} {category} at ({pos['x']}, {pos['y']})")
    pyautogui.moveTo(pos["x"], pos["y"])
    pyautogui.click()
    return True

def test_all_sequences(recorder: ClickRecorder):
    """Test all recorded sequences"""
    if not recorder.sequences:
        print("No sequences recorded yet!")
        return

    print("\nTest options:")
    print("1. Test all sequences")
    print("2. Test by category")
    print("3. Test specific item")
    print("4. Test all items in category")
    
    choice = input("\nChoice (1-4): ")
    
    if choice == "1":
        print("\nWill test all sequences")
        print("Switch to POE window...")
        time.sleep(0.5)
        
        for item_name, sequences in sorted(recorder.sequences.items()):
            print(f"\nTesting {item_name}...")
            for seq_type in sequences:
                print(f"Playing {seq_type} sequence...")
                recorder.play_sequence(item_name, seq_type)
                time.sleep(0.1)
                
    elif choice == "2":
        categories = set()
        # Collect all categories
        for item_name in recorder.sequences:
            if item_name.startswith("i_want_") or item_name.startswith("i_have_"):
                clean_name = item_name[7:]  # Remove i_want_ or i_have_
                category = get_category_for_item(clean_name)
                categories.add(category)
        
        print("\nAvailable categories:")
        for category in CATEGORY_ORDER:
            if category in categories:
                print(f"- {category}")
            
        category = input("\nEnter category to test: ")
        side = input("Which side to test (want/have/both)? ").lower()
        
        print("\nSwitch to POE window...")
        time.sleep(0.5)
        
        # Test i_want sequences for category
        if side in ["want", "both"]:
            for item_name in sorted(recorder.sequences):
                if item_name.startswith("i_want_"):
                    clean_name = item_name[7:]
                    if get_category_for_item(clean_name) == category:
                        print(f"\nTesting {item_name}...")
                        recorder.play_sequence(item_name, "select")
                        time.sleep(0.1)
                        
        # Test i_have sequences for category
        if side in ["have", "both"]:
            for item_name in sorted(recorder.sequences):
                if item_name.startswith("i_have_"):
                    clean_name = item_name[7:]
                    if get_category_for_item(clean_name) == category:
                        print(f"\nTesting {item_name}...")
                        recorder.play_sequence(item_name, "select")
                        time.sleep(0.1)
                        
    elif choice == "3":
        print("\nAvailable items:")
        for item_name in sorted(recorder.sequences):
            print(f"- {item_name}")
            
        item_name = input("\nEnter item name to test: ")
        if item_name in recorder.sequences:
            print("\nSwitch to POE window...")
            time.sleep(0.5)
            
            for seq_type in recorder.sequences[item_name]:
                print(f"\nPlaying {seq_type} sequence...")
                recorder.play_sequence(item_name, seq_type)
                time.sleep(0.1)
        else:
            print("Item not found!")
            
    elif choice == "4":
        # Load all items from tradeables.json
        tradeable_file = Path("data/tradeables.json")
        if not tradeable_file.exists():
            print("tradeables.json not found!")
            return
            
        with open(tradeable_file) as f:
            data = json.load(f)
            
        # Show available categories from tradeables.json
        print("\nAvailable categories:")
        for category in data.keys():
            print(f"- {category}")
            
        category = input("\nEnter category to test: ")
        if category not in data:
            print("Category not found!")
            return
            
        side = input("Which side to test (want/have/both)? ").lower()
        if side not in ["want", "have", "both"]:
            print("Invalid side!")
            return
            
        print("\nSwitch to POE window...")
        time.sleep(0.5)
        
        # Get all items in the category
        items = []
        category_data = data[category]
        if isinstance(category_data, list):
            items.extend(category_data)
        elif isinstance(category_data, dict):
            for subcategory in category_data.values():
                if isinstance(subcategory, list):
                    items.extend(subcategory)
                    
        # Test each item
        for item in sorted(items):
            if side in ["want", "both"]:
                sequence_name = f"i_want_{item}"
                if sequence_name in recorder.sequences:
                    print(f"\nTesting {sequence_name}...")
                    recorder.play_sequence(sequence_name, "select")
                    time.sleep(0.1)
                    
            if side in ["have", "both"]:
                sequence_name = f"i_have_{item}"
                if sequence_name in recorder.sequences:
                    print(f"\nTesting {sequence_name}...")
                    recorder.play_sequence(sequence_name, "select")
                    time.sleep(0.1)

def find_position():
    """Tool to help find cursor positions"""
    print("\nPosition Finder")
    print("==============")
    print("This tool will help you find cursor positions.")
    print("Instructions:")
    print("1. Switch to POE window")
    print("2. Move your cursor to the position you want to check")
    print("3. Switch back here and press Enter to see coordinates")
    print("4. Press 'q' to quit\n")
    
    while True:
        command = input("Press Enter to get position, 'q' to quit: ")
        if command.lower() == 'q':
            break
            
        pos = pyautogui.position()
        print(f"Current position: ({pos.x}, {pos.y})")

def rerecord_tradeables(recorder: ClickRecorder):
    """Re-record positions for existing tradeables"""
    if not recorder.sequences:
        print("No sequences recorded yet!")
        return

    # Load tradeables.json to get category structure
    tradeable_file = Path("data/tradeables.json")
    if not tradeable_file.exists():
        print("tradeables.json not found!")
        return
        
    with open(tradeable_file) as f:
        data = json.load(f)
        
    # Show available categories
    print("\nAvailable categories:")
    for category in data.keys():
        print(f"- {category}")
        
    category = input("\nEnter category to re-record (or 'all' for everything): ")
    if category != "all" and category not in data:
        print("Category not found!")
        return
        
    # Get items to re-record
    items_to_record = []
    if category == "all":
        # Get all items from all categories
        for cat_data in data.values():
            if isinstance(cat_data, list):
                items_to_record.extend(cat_data)
            elif isinstance(cat_data, dict):
                for subcategory in cat_data.values():
                    if isinstance(subcategory, list):
                        items_to_record.extend(subcategory)
    else:
        # Get items from specific category
        category_data = data[category]
        if isinstance(category_data, list):
            items_to_record.extend(category_data)
        elif isinstance(category_data, dict):
            for subcategory in category_data.values():
                if isinstance(subcategory, list):
                    items_to_record.extend(subcategory)
                    
    if not items_to_record:
        print("No items found to re-record!")
        return
        
    print(f"\nFound {len(items_to_record)} items to re-record")
    print("For each item:")
    print("1. Position your mouse over the item")
    print("2. Press Enter to record the position")
    print("3. The position will be used for both i_want and i_have")
    print("(The tab and category positions are handled automatically)")
    print("\nPress Enter to start, or 'q' to cancel...")
    
    if input().lower() == 'q':
        return
        
    print("\nSwitch to POE window...")
    time.sleep(0.5)
    
    for item in sorted(items_to_record):
        print(f"\n=== Re-recording position for {item} ===")
        print("Position your mouse over the item and press Enter")
        print("Press 'q' to skip this item")
        
        try:
            while True:
                command = input()
                
                if command.lower() == 'q':
                    print("Skipping item...")
                    break
                    
                pos = pyautogui.position()
                item_click = {"x": pos.x, "y": pos.y}
                print(f"Recorded position at ({pos.x}, {pos.y})")
                
                # Update both i_want and i_have sequences
                recorder.sequences[f"i_want_{item}"] = {"select": [item_click]}
                recorder.sequences[f"i_have_{item}"] = {"select": [item_click]}
                recorder.save_sequences()
                
                print(f"Updated sequences for both i_want_{item} and i_have_{item}")
                break
                
        except pyautogui.FailSafeException:
            print("\nRecording aborted (mouse moved to corner)")
            break
        
        print("\nContinue with next item? (y/n)")
        if input().lower() != 'y':
            break
            
    print("\nRe-recording complete!")

def delete_sequences(recorder: ClickRecorder):
    """Delete recorded sequences"""
    if not recorder.sequences:
        print("No sequences recorded yet!")
        return

    print("\nDelete options:")
    print("1. Delete all sequences")
    print("2. Delete by category")
    print("3. Delete specific item")
    
    choice = input("\nChoice (1-3): ")
    
    if choice == "1":
        confirm = input("Are you sure you want to delete ALL sequences? (y/n): ")
        if confirm.lower() == 'y':
            recorder.delete_all_sequences()
            
    elif choice == "2":
        categories = set()
        # Collect all categories
        for item_name in recorder.sequences:
            if item_name.startswith("i_want_") or item_name.startswith("i_have_"):
                clean_name = item_name[7:]  # Remove i_want_ or i_have_
                category = get_category_for_item(clean_name)
                categories.add(category)
        
        print("\nAvailable categories:")
        for category in CATEGORY_ORDER:
            if category in categories:
                print(f"- {category}")
            
        category = input("\nEnter category to delete: ")
        side = input("Which side to delete (want/have/both)? ").lower()
        
        confirm = input(f"Are you sure you want to delete all {side} sequences for category {category}? (y/n): ")
        if confirm.lower() == 'y':
            items_to_delete = []
            if side in ["want", "both"]:
                for item_name in recorder.sequences:
                    if item_name.startswith("i_want_"):
                        clean_name = item_name[7:]
                        if get_category_for_item(clean_name) == category:
                            items_to_delete.append(item_name)
                            
            if side in ["have", "both"]:
                for item_name in recorder.sequences:
                    if item_name.startswith("i_have_"):
                        clean_name = item_name[7:]
                        if get_category_for_item(clean_name) == category:
                            items_to_delete.append(item_name)
            
            for item_name in items_to_delete:
                recorder.delete_sequence(item_name)
            print(f"Deleted {len(items_to_delete)} sequences")
                        
    elif choice == "3":
        print("\nAvailable items:")
        for item_name in sorted(recorder.sequences):
            print(f"- {item_name}")
            
        item_name = input("\nEnter item name to delete: ")
        if item_name in recorder.sequences:
            sequence_types = list(recorder.sequences[item_name].keys())
            print(f"\nSequence types for {item_name}:")
            for i, seq_type in enumerate(sequence_types, 1):
                print(f"{i}. {seq_type}")
            print(f"{len(sequence_types) + 1}. All types")
            
            type_choice = input(f"\nWhich type to delete (1-{len(sequence_types) + 1})? ")
            try:
                type_idx = int(type_choice) - 1
                if 0 <= type_idx < len(sequence_types):
                    sequence_type = sequence_types[type_idx]
                    confirm = input(f"Delete {sequence_type} sequence for {item_name}? (y/n): ")
                    if confirm.lower() == 'y':
                        recorder.delete_sequence(item_name, sequence_type)
                elif type_idx == len(sequence_types):
                    confirm = input(f"Delete ALL sequences for {item_name}? (y/n): ")
                    if confirm.lower() == 'y':
                        recorder.delete_sequence(item_name)
            except ValueError:
                print("Invalid choice!")
        else:
            print("Item not found!")

def main():
    recorder = ClickRecorder()
    
    while True:
        print("\nClick Sequence Recorder")
        print("=====================")
        print("1. Record New Sequence")
        print("2. Play Sequence")
        print("3. Record All Tradeables")
        print("4. Find Position")
        print("5. Test All Sequences")
        print("6. Re-record Tradeables")
        print("7. Delete Sequences")
        print("8. Exit")
        
        choice = input("\nChoice: ")
        
        if choice == "1":
            item_name = input("Item name (e.g., divine_orb, soul_core_azcapa): ")
            
            print("\nSequence Types:")
            for seq_type, desc in SEQUENCE_TYPES.items():
                print(f"- {seq_type}: {desc}")
            sequence_type = input("\nSequence type (default: select): ") or "select"
            
            print("\nSwitch to POE window...")
            time.sleep(0.5)  # Give time to switch windows
            recorder.record_sequence(item_name, sequence_type)
            
        elif choice == "2":
            if not recorder.sequences:
                print("No sequences recorded yet!")
                continue
                
            print("\nAvailable sequences:")
            for item, types in recorder.sequences.items():
                print(f"\n{item}:")
                for seq_type in types:
                    print(f"- {seq_type}: {SEQUENCE_TYPES[seq_type]}")
            
            item_name = input("\nItem name: ")
            sequence_type = input("Sequence type (default: select): ") or "select"
            print("\nSwitch to POE window...")
            time.sleep(0.5)  # Give time to switch windows
            recorder.play_sequence(item_name, sequence_type)
            
        elif choice == "3":  # Record all tradeables
            tradeables = load_tradeables()
            if not tradeables:
                print("No tradeables found!")
                continue
                
            print(f"\nFound {len(tradeables)} tradeable items")
            print("This will help you record sequences for all items")
            print("For each item:")
            print("1. Record the item position once")
            print("2. It will be used for both i_want and i_have sequences")
            print("(The tab and category positions are added automatically)")
            
            for item in sorted(tradeables):
                # Clean the item name for use as identifier
                clean_name = item.lower().replace(" ", "_").replace("'", "")
                
                # Record item position once
                print(f"\n=== Recording position for {clean_name} ===")
                print("Position your mouse over the item and press Enter")
                print("Press 'q' when done")
                
                # Record the position
                try:
                    while True:
                        command = input()
                        
                        if command.lower() == 'q':
                            break
                            
                        pos = pyautogui.position()
                        item_click = {"x": pos.x, "y": pos.y}
                        print(f"Recorded position at ({pos.x}, {pos.y})")
                        
                        # Create i_want sequence
                        i_want_clicks = [item_click]  # Just the item click
                        
                        # Create i_have sequence
                        i_have_clicks = [item_click]  # Just the item click
                        
                        # Save both sequences
                        recorder.sequences[f"i_want_{clean_name}"] = {"select": i_want_clicks}
                        recorder.sequences[f"i_have_{clean_name}"] = {"select": i_have_clicks}
                        recorder.save_sequences()
                        
                        print(f"Saved sequences for both i_want_{clean_name} and i_have_{clean_name}")
                        break
                        
                except pyautogui.FailSafeException:
                    print("\nRecording aborted (mouse moved to corner)")
                    break
                
                print("\nContinue with next item? (y/n)")
                if input().lower() != 'y':
                    break
                
        elif choice == "4":
            find_position()
            
        elif choice == "5":
            test_all_sequences(recorder)
            
        elif choice == "6":
            rerecord_tradeables(recorder)
            
        elif choice == "7":
            delete_sequences(recorder)
            
        elif choice == "8":
            break

if __name__ == "__main__":
    main() 