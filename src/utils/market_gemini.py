import os
import json
from pathlib import Path
import google.generativeai as genai
from PIL import Image
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from src.models.market_data import MarketData
from .gemini import setup_gemini, save_raw_response

# Load environment variables from .env file
load_dotenv()

def setup_gemini():
    """Setup Gemini API with key from environment"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash-exp')

def get_latest_screenshot() -> Path:
    """Get the path to the most recent market screenshot"""
    screenshot_dir = Path("data/market_screenshots")
    if not screenshot_dir.exists():
        raise FileNotFoundError("Market screenshots directory not found")
        
    # Get all png files and sort by modification time
    screenshots = list(screenshot_dir.glob("*.png"))
    if not screenshots:
        raise FileNotFoundError("No market screenshots found")
        
    return max(screenshots, key=lambda p: p.stat().st_mtime)

def save_raw_response(response_text: str, image_path: Path):
    """Save raw Gemini response to file"""
    # Create raw_responses directory if it doesn't exist
    data_dir = Path("data/market_raw_responses")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename based on original screenshot name
    base_name = image_path.stem
    response_path = data_dir / f"{base_name}_raw.txt"
    
    # Save raw response
    with open(response_path, 'w') as f:
        f.write(response_text)
    
    print(f"Raw response saved to: {response_path}")
    return response_path

def analyze_market_image(image_path: Path) -> Optional[MarketData]:
    """Analyze market screenshot using Gemini Vision API"""
    # Load the image
    img = Image.open(image_path)
    
    # Create the prompt
    prompt = """
    Capture the important information from this image, and place in a neat json format like:
    {
        "i_want": "(name)",
        "i_have": "(name)",
        "market_ratio": "(ratio)",
        "available_trades": [
            {"ratio": "x:1", "stock": "y"}
        ],
        "competing_trades": [
            {"ratio": "x:1", "stock": "y"}
        ]
    }
    
    Only include the JSON data, no other text. Ensure all numbers are numeric (not strings) except for ratios.
    """
    
    # Setup Gemini
    model = setup_gemini()
    
    # Generate response
    response = model.generate_content([prompt, img])
    
    # Save raw response
    save_raw_response(response.text, image_path)
    
    # Extract JSON from response
    try:
        # Find JSON content between curly braces
        json_str = response.text
        if not json_str.strip().startswith('{'):
            json_str = '{' + json_str.split('{', 1)[1]
        if not json_str.strip().endswith('}'):
            json_str = json_str.rsplit('}', 1)[0] + '}'
            
        # Parse JSON
        data = json.loads(json_str)
        
        # Convert to MarketData object
        market_data = MarketData.from_dict(data)
        return market_data
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        print(f"Raw response: {response.text}")
        return None

def save_market_data(data: Dict[str, Any], image_path: Path):
    """Save market data to JSON file"""
    # Create market_data directory if it doesn't exist
    data_dir = Path("data/market_data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename based on original screenshot name
    base_name = image_path.stem
    json_path = data_dir / f"{base_name}.json"
    
    # Save data
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Market data saved to: {json_path}")
    return json_path

def analyze_latest_market():
    """Analyze the latest market screenshot and save results"""
    try:
        # Get latest screenshot
        image_path = get_latest_screenshot()
        print(f"Analyzing screenshot: {image_path}")
        
        # Analyze image
        market_data = analyze_market_image(image_path)
        if not market_data:
            print("Failed to analyze market data")
            return
            
        # Save results
        json_path = save_market_data(market_data.to_dict(), image_path)
        
        # Print results
        print("\nMarket Analysis Results:")
        print(json.dumps(market_data.to_dict(), indent=2))
        
        return market_data
        
    except Exception as e:
        print(f"Error analyzing market: {e}")
        return None

if __name__ == "__main__":
    analyze_latest_market() 