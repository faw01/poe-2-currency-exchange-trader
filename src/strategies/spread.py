from datetime import datetime
from typing import Dict, Optional
from .base_strategy import BaseStrategy
import pyautogui

class SimpleSpreadStrategy(BaseStrategy):
    def __init__(self, min_profit: float = 0.01, trade_amount: int = 100):
        super().__init__(min_profit)
        self.trade_amount = trade_amount
        
    def analyze_opportunity(self, rates: Dict[str, float]) -> Optional[Dict]:
        """Look for profitable spreads in the same currency pair"""
        available = rates['available_trades']
        if not available:
            return None
            
        min_rate = min(available)
        max_rate = max(available)
        
        spread = (max_rate - min_rate) / min_rate
        
        if spread > self.min_profit:
            return {
                'timestamp': datetime.now(),
                'buy_rate': min_rate,
                'sell_rate': max_rate,
                'profit': spread,
                'amount': self.trade_amount
            }
        return None
        
    def execute_trade(self, trade_info: Dict) -> bool:
        """Execute the trade using mouse clicks"""
        try:
            # These coordinates need to be configured
            buy_coords = (800, 400)  # Example coordinates
            sell_coords = (800, 450)  # Example coordinates
            
            # Click buy order
            pyautogui.click(buy_coords)
            pyautogui.write(str(trade_info['amount']))
            pyautogui.press('enter')
            
            # Click sell order
            pyautogui.click(sell_coords)
            pyautogui.write(str(trade_info['amount']))
            pyautogui.press('enter')
            
            self.record_trade(trade_info)
            return True
            
        except Exception as e:
            print(f"Trade execution failed: {e}")
            return False