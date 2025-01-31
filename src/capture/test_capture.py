from .screen_capture import ScreenCapture
import time

def countdown(seconds: int):
    """Display a countdown timer"""
    for i in range(seconds, 0, -1):
        print(f"Capturing in {i} seconds... (Alt-Tab to POE now)", end='\r')
        time.sleep(1)
    print(" " * 50, end='\r')  # Clear the line

def easy_calibrate(capture: ScreenCapture):
    """Guide user through calibrating all trading elements"""
    print("\nEasy Calibration Wizard")
    print("=====================")
    print("This will guide you through setting up all trading elements.")
    print("\nFor each element:")
    print("1. Switch to POE window")
    print("2. Position mouse over the element")
    print("3. Switch back here and press Enter")
    print("4. Use arrow keys to adjust the capture region")
    print("5. Press Enter to save or ESC to retry")
    input("\nPress Enter when ready to start...")

    # Define all elements we need to calibrate
    elements = [
        ("i_want_currency", "'I want' currency selector"),
        ("i_have_currency", "'I have' currency selector"),
        ("i_want_amount", "'I want' amount input"),
        ("i_have_amount", "'I have' amount input"),
        ("market_ratio", "Market ratio/exchange rate"),
        ("trade_button", "Trade button")
    ]

    # Calibrate each element
    for name, description in elements:
        while True:
            print(f"\n=== Calibrating: {description} ===")
            if capture.calibrate_element(name, description):
                break
            retry = input("\nCalibration cancelled. Retry? (y/n): ").lower()
            if retry != 'y':
                return False

    print("\n✓ Calibration complete!")
    print("Let's save a debug image to verify everything...")
    print("\n1. Switch to POE window when countdown starts")
    print("2. Position your windows/UI as needed")
    input("Press Enter to start 5-second countdown...")
    countdown(5)
    capture.save_debug_image('debug_capture')
    print("✓ Saved debug image as debug_capture.png")
    print("  Green dots = Click positions")
    print("  Red boxes = Capture regions")
    return True

def main():
    """Test the screen capture functionality"""
    capture = ScreenCapture()
    
    print("POE2 Trading Setup")
    print("=================")
    print("\nThis tool helps you set up automated trading.")
    print("You'll need to calibrate each UI element once.")
    
    while True:
        print("\nOptions:")
        print("1. Easy Calibrate (Recommended)")
        print("2. Test Trading Workflow")
        print("3. Save Debug Image")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ")
        
        if choice == '1':
            easy_calibrate(capture)
            
        elif choice == '2':
            if not capture.elements:
                print("Please calibrate positions first!")
                continue
                
            print("\nAvailable elements:", ", ".join(capture.elements.keys()))
            print("\nTest options:")
            print("1. Click element")
            print("2. Read text")
            subchoice = input("Enter test type (1-2): ")
            
            name = input("Element name to test: ")
            
            if subchoice == '1':
                capture.click(name)
            elif subchoice == '2':
                text = capture.capture_text(name)
                print(f"Captured text: {text}")
            
        elif choice == '3':
            print("\nPreparing to capture debug image...")
            print("1. Switch to POE window when countdown starts")
            print("2. Position your windows/UI as needed")
            input("Press Enter to start 5-second countdown...")
            countdown(5)
            capture.save_debug_image('debug_capture')
            print("✓ Saved debug image as debug_capture.png")
            print("  Green dots = Click positions")
            print("  Red boxes = Capture regions")
            
        elif choice == '4':
            break
            
if __name__ == "__main__":
    main() 