import os
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_gemini():
    """Setup Gemini API with key from environment"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables or .env file")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-pro-vision')

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