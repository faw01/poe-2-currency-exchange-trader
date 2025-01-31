import pyautogui
import numpy as np
from typing import Dict, Tuple, Optional, List
import json
import time

class FastCapture:
    def __init__(self):
        """Initialize fast screen capture with minimal delay"""
        pyautogui.PAUSE = 0.01  # Minimal delay between actions
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        self.elements: Dict[str, Dict] = {}
        self.validation_size = 3  # Size of validation region (3x3 pixels)
        self.color_threshold = 20  # Default color difference threshold
        
    def calibrate_element(self, name: str, description: str) -> bool:
        """Calibrate an element with click position and pixel color validation"""
        print(f"\nCalibrating element: {description}")
        print("1. Switch to POE window")
        print("2. Position mouse over the element")
        print("3. Switch back here and press Enter")
        input("Press Enter when ready...")
        
        # Get click position and validation color
        pos = pyautogui.position()
        half_size = self.validation_size // 2
        region = (pos[0]-half_size, pos[1]-half_size, self.validation_size, self.validation_size)
        screenshot = pyautogui.screenshot(region=region)
        pixel_colors = np.array(screenshot)
        center_color = pixel_colors[half_size, half_size].tolist()
        
        # Save element data
        self.elements[name] = {
            'click_pos': pos,
            'validation_color': center_color,
            'last_valid': time.time()
        }
        
        print(f"✓ Saved element '{name}'")
        print(f"  Click position: {pos}")
        print(f"  Validation color: {center_color}")
        return True
    
    def validate_element(self, name: str, threshold: Optional[int] = None) -> bool:
        """Validate element exists by checking pixel color"""
        if name not in self.elements:
            return False
            
        element = self.elements[name]
        threshold = threshold or self.color_threshold
        pos = element['click_pos']
        expected_color = np.array(element['validation_color'])
        
        # Get current color
        half_size = self.validation_size // 2
        region = (pos[0]-half_size, pos[1]-half_size, self.validation_size, self.validation_size)
        screenshot = pyautogui.screenshot(region=region)
        current_color = np.array(screenshot)[half_size, half_size]
        
        # Check color difference
        color_diff = np.abs(expected_color - current_color).max()
        is_valid = color_diff <= threshold
        
        if is_valid:
            element['last_valid'] = time.time()
            
        return is_valid
    
    def click(self, name: str, validate: bool = True) -> bool:
        """Click element with optional validation"""
        if name not in self.elements:
            return False
            
        if validate and not self.validate_element(name):
            print(f"Warning: Element '{name}' validation failed")
            return False
            
        pos = self.elements[name]['click_pos']
        pyautogui.click(*pos)
        return True
    
    def batch_click(self, names: list, validate: bool = True):
        """Click multiple elements in sequence"""
        for name in names:
            self.click(name, validate)
            
    def save_calibration(self, filename: str = 'calibration.json'):
        """Save calibrated elements to file"""
        data = {}
        for name, element in self.elements.items():
            data[name] = {
                'click_pos': element['click_pos'],
                'validation_color': element['validation_color']
            }
            
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
    def load_calibration(self, filename: str = 'calibration.json'):
        """Load calibrated elements from file"""
        try:
            with open(filename) as f:
                data = json.load(f)
                
            for name, element in data.items():
                self.elements[name] = {
                    'click_pos': tuple(element['click_pos']),
                    'validation_color': element['validation_color'],
                    'last_valid': time.time()
                }
                
            return True
        except Exception as e:
            print(f"Error loading calibration: {e}")
            return False