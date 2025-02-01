from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Trade:
    ratio: str
    stock: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert Trade to dictionary"""
        return {
            "ratio": self.ratio ,
            "stock": self.stock
        }

@dataclass
class MarketData:
    i_want: str
    i_have: str
    market_ratio: str
    available_trades: List[Trade]
    competing_trades: List[Trade]

    def to_dict(self) -> Dict[str, Any]:
        """Convert MarketData to dictionary"""
        return {
            "i_want": self.i_want,
            "i_have": self.i_have,
            "market_ratio": self.market_ratio,
            "available_trades": [t.to_dict() for t in self.available_trades],
            "competing_trades": [t.to_dict() for t in self.competing_trades]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketData':
        """Create MarketData from dictionary"""
        return cls(
            i_want=data['i_want'],
            i_have=data['i_have'],
            market_ratio=data['market_ratio'],
            available_trades=[Trade(**t) for t in data['available_trades']],
            competing_trades=[Trade(**t) for t in data['competing_trades']]
        ) 