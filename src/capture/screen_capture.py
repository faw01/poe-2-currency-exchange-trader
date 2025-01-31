import pyautogui
import cv2
import numpy as np
import pytesseract
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional
import time
import keyboard

@dataclass
class CaptureElement:
    """A screen element with position and optional capture region"""
    name: str
    click_pos: Tuple[int, int]  # Where to click
    capture_region: Tuple[int, int, int, int] = None  # Region to capture (x, y, width, height)
    validation_color: Optional[np.ndarray] = None  # Color to validate against
    last_capture: Optional[np.ndarray] = None  # Cache last capture
    last_text: Optional[str] = None  # Cache last text

class ScreenCapture:
    def __init__(self):
        """Initialize screen capture with minimal delay"""
        pyautogui.PAUSE = 0.01  # Minimal delay between actions
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        self.elements: Dict[str, CaptureElement] = {}
        
        # Performance settings
        self.fast_mode = True  # Always use fast mode for trading
        self.cache_enabled = True  # When True, caches captures
        self.batch_size = 10  # Number of actions to batch together
        
        # Default region size around click point
        self.default_region_size = (100, 30)  # width, height
        
    def calibrate_element(self, name: str, description: str) -> bool:
        """Calibrate both click position and capture region in one step"""
        print(f"\nCalibrating element: {description}")
        print("1. Switch to POE window")
        print("2. Position your mouse over the element")
        print("3. Switch back here and press Enter to capture position")
        print("4. Use arrow keys to adjust the region size")
        print("5. Press 'C' to pick validation color")
        print("6. Press Enter to save, ESC to cancel")
        input("Press Enter when ready...")
        
        # Get click position
        click_pos = pyautogui.position()
        width, height = self.default_region_size
        
        # Create initial region
        x = click_pos[0] - width//2
        y = click_pos[1] - height//2
        region = (x, y, width, height)
        
        # Take a screenshot for preview
        screen = pyautogui.screenshot()
        screen = np.array(screen)
        screen = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
        
        # Store validation color
        validation_color = None
        
        while True:
            preview = screen.copy()
            # Draw click position
            cv2.circle(preview, click_pos, 5, (0, 255, 0), -1)
            # Draw region
            cv2.rectangle(preview, (x, y), (x+width, y+height), (0, 0, 255), 2)
            
            # Draw validation color if picked
            if validation_color is not None:
                cv2.circle(preview, (x+10, y+10), 10, validation_color.tolist(), -1)
            
            # Show preview
            cv2.imshow('Preview - ↑↓←→:adjust size, C:pick color, Enter:save, ESC:cancel', preview)
            key = cv2.waitKey(100)
            
            # Handle key presses
            if key == 27:  # ESC
                cv2.destroyAllWindows()
                return False
            elif key == 13:  # Enter
                if validation_color is None:
                    print("Please pick a validation color first (press 'C')")
                    continue
                break
            elif key == ord('c'):  # Pick validation color
                # Get color at click position
                validation_color = screen[click_pos[1], click_pos[0]]
                print(f"Picked validation color: {validation_color}")
            elif key == 82:  # Up arrow
                height -= 2
            elif key == 84:  # Down arrow
                height += 2
            elif key == 81:  # Left arrow
                width -= 2
            elif key == 83:  # Right arrow
                width += 2
                
            # Update region
            x = click_pos[0] - width//2
            y = click_pos[1] - height//2
            region = (x, y, width, height)
        
        # Cleanup
        cv2.destroyAllWindows()
        
        # Save the element
        self.elements[name] = CaptureElement(
            name=name,
            click_pos=click_pos,
            capture_region=region,
            validation_color=validation_color
        )
        
        print(f"✓ Saved element '{name}':")
        print(f"  Click: {click_pos}")
        print(f"  Region: {region}")
        print(f"  Validation color: {validation_color}")
        return True
        
    def calibrate_click(self, name: str, description: str) -> bool:
        """Calibrate a click position"""
        print(f"\nCalibrating click position for: {description}")
        print("1. Switch to target window")
        print("2. Move mouse to position")
        print("3. Switch back here")
        input("Press Enter when ready...")
        
        pos = pyautogui.position()
        self.elements[name] = CaptureElement(name=name, click_pos=pos)
        print(f"✓ Saved position: {pos}")
        return True
        
    def calibrate_region(self, name: str, description: str) -> bool:
        """Calibrate a region to capture from"""
        print(f"\nCalibrating capture region for: {description}")
        
        # Get top-left corner
        print("\nSelect top-left corner:")
        input("Position mouse and press Enter...")
        x1, y1 = pyautogui.position()
        
        # Get bottom-right corner
        print("\nSelect bottom-right corner:")
        input("Position mouse and press Enter...")
        x2, y2 = pyautogui.position()
        
        # Create region
        region = (x1, y1, x2-x1, y2-y1)
        
        # If this is a new element
        if name not in self.elements:
            self.elements[name] = CaptureElement(name=name, click_pos=(x1, y1), capture_region=region)
        else:
            # Update existing element's region
            self.elements[name].capture_region = region
            
        print(f"✓ Saved region: {region}")
        return True
        
    def click(self, name: str, fast: bool = False):
        """Click a calibrated position"""
        if name not in self.elements:
            print(f"Element '{name}' not calibrated!")
            return False
            
        if fast or self.fast_mode:
            pyautogui.moveTo(*self.elements[name].click_pos)
            pyautogui.click()
        else:
            pyautogui.click(*self.elements[name].click_pos)
        return True
        
    def batch_click(self, names: List[str]):
        """Click multiple positions in rapid succession"""
        for name in names:
            if name in self.elements:
                pyautogui.moveTo(*self.elements[name].click_pos)
                pyautogui.click()
                if not self.fast_mode:
                    time.sleep(0.05)
                    
    def type_text(self, text: str, enter: bool = True):
        """Type text with minimal delay"""
        if self.fast_mode:
            pyautogui.write(text, interval=0.01)
        else:
            pyautogui.write(text)
            
        if enter:
            pyautogui.press('enter')
            
    def capture_text(self, name: str, force_refresh: bool = False) -> str:
        """Capture and read text from a calibrated region"""
        if name not in self.elements or not self.elements[name].capture_region:
            print(f"Region '{name}' not calibrated!")
            return ""
            
        element = self.elements[name]
        
        # Return cached text if available and cache is enabled
        if self.cache_enabled and not force_refresh and element.last_text is not None:
            return element.last_text
            
        try:
            # Take screenshot of region
            region = element.capture_region
            screenshot = pyautogui.screenshot(region=region)
            
            # Convert to grayscale
            image = np.array(screenshot)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
            
            # Cache the capture
            if self.cache_enabled:
                element.last_capture = gray
            
            # Use OCR to read text
            text = pytesseract.image_to_string(gray)
            text = text.strip()
            
            # Cache the text
            if self.cache_enabled:
                element.last_text = text
                
            return text
            
        except Exception as e:
            print(f"Error capturing text: {str(e)}")
            return ""
            
    def batch_capture(self, names: List[str]) -> Dict[str, str]:
        """Capture text from multiple regions quickly"""
        results = {}
        for name in names:
            if name in self.elements and self.elements[name].capture_region:
                results[name] = self.capture_text(name)
        return results
        
    def clear_cache(self, name: Optional[str] = None):
        """Clear cached captures and text"""
        if name:
            if name in self.elements:
                self.elements[name].last_capture = None
                self.elements[name].last_text = None
        else:
            for element in self.elements.values():
                element.last_capture = None
                element.last_text = None
                
    def save_debug_image(self, name: str = 'debug'):
        """Save a debug image showing all calibrated elements"""
        screen = pyautogui.screenshot()
        screen = np.array(screen)
        screen = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
        
        # Draw all elements
        for element in self.elements.values():
            # Draw click position
            x, y = element.click_pos
            cv2.circle(screen, (x, y), 5, (0, 255, 0), -1)
            cv2.putText(screen, f"{element.name} click", (x+5, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Draw region if exists
            if element.capture_region:
                x, y, w, h = element.capture_region
                cv2.rectangle(screen, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(screen, f"{element.name} region", (x, y-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        cv2.imwrite(f'{name}.png', screen)