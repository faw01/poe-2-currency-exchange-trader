from fast_capture import FastCapture
import time

def countdown(seconds: int):
    """Simple countdown timer"""
    for i in range(seconds, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)

def main():
    """Test the fast screen capture functionality"""
    capture = FastCapture()
    
    print("POE2 Trading Setup (Fast Mode)")
    print("===========================")
    print("\nThis tool helps you set up automated trading using a simplified approach.")
    print("You'll need to calibrate each UI element once.")
    
    while True:
        print("\nOptions:")
        print("1. Calibrate New Element")
        print("2. Test Element")
        print("3. Save Calibration")
        print("4. Load Calibration")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ")
        
        if choice == '1':
            name = input("Enter element name: ")
            desc = input("Enter element description: ")
            print("\nPreparing to calibrate...")
            countdown(3)
            capture.calibrate_element(name, desc)
            
        elif choice == '2':
            if not capture.elements:
                print("Please calibrate elements first!")
                continue
                
            print("\nAvailable elements:", ", ".join(capture.elements.keys()))
            name = input("Enter element name to test: ")
            
            print("\nTest options:")
            print("1. Validate element")
            print("2. Click element")
            subchoice = input("Enter test type (1-2): ")
            
            print("\nPreparing to test...")
            countdown(3)
            
            if subchoice == '1':
                if capture.validate_element(name):
                    print("✓ Element validated successfully")
                else:
                    print("✗ Element validation failed")
            elif subchoice == '2':
                if capture.click(name):
                    print("✓ Click successful")
                else:
                    print("✗ Click failed")
            
        elif choice == '3':
            filename = input("Enter filename to save (default: calibration.json): ").strip()
            if not filename:
                filename = 'calibration.json'
            capture.save_calibration(filename)
            print(f"✓ Saved calibration to {filename}")
            
        elif choice == '4':
            filename = input("Enter filename to load (default: calibration.json): ").strip()
            if not filename:
                filename = 'calibration.json'
            if capture.load_calibration(filename):
                print(f"✓ Loaded calibration from {filename}")
            
        elif choice == '5':
            break
            
if __name__ == '__main__':
    main()