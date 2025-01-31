from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseStrategy(ABC):
    def __init__(self, min_profit: float = 0.01):
        self.min_profit = min_profit
        self.trade_history = []
        
    @abstractmethod
    def analyze_opportunity(self, rates: Dict[str, float]) -> Optional[Dict]:
        """Analyze current rates for trading opportunities"""
        pass
        
    @abstractmethod
    def execute_trade(self, trade_info: Dict) -> bool:
        """Execute a trade based on the opportunity"""
        pass
        
    def record_trade(self, trade_info: Dict):
        """Record trade details for analysis"""
        self.trade_history.append({
            'timestamp': trade_info.get('timestamp'),
            'buy_rate': trade_info.get('buy_rate'),
            'sell_rate': trade_info.get('sell_rate'),
            'profit': trade_info.get('profit'),
            'amount': trade_info.get('amount')
        })
        
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        if not self.trade_history:
            return {"trades": 0, "profit": 0}
            
        total_profit = sum(trade['profit'] for trade in self.trade_history)
        return {
            "trades": len(self.trade_history),
            "profit": total_profit,
            "avg_profit": total_profit / len(self.trade_history)
        }