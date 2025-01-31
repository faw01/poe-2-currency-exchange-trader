from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import numpy as np
from collections import defaultdict

@dataclass
class BasicOpportunity:
    buy_currency: str
    sell_currency: str
    buy_ratio: str
    sell_ratio: str
    potential_profit: float
    trade_volume: int
    confidence: float

@dataclass
class TriangleOpportunity:
    step1: Tuple[str, str, str]  # (from_currency, to_currency, ratio)
    step2: Tuple[str, str, str]
    step3: Tuple[str, str, str]
    total_profit: float
    min_volume: int
    confidence: float

@dataclass
class MarketMakingOpportunity:
    currency_pair: Tuple[str, str]  # (base, quote)
    bid_price: str
    ask_price: str
    spread: float
    volume: int
    volatility: float
    confidence: float

@dataclass
class MarketData:
    i_want: str
    i_have: str
    market_ratio: str
    available_trades: List[Dict[str, any]]
    competing_trades: List[Dict[str, any]]
    timestamp: datetime

class TradingStrategies:
    def __init__(self):
        self.market_history: Dict[str, List[Dict]] = defaultdict(list)
        self.min_profit_threshold = 0.015  # 1.5% minimum profit
        self.max_trade_volume = 1000
        self.volatility_window = timedelta(minutes=30)
        self.known_currencies: Set[str] = set()

    def load_market_data(self, json_path: Path) -> MarketData:
        """Load market data from JSON file"""
        with open(json_path) as f:
            data = json.load(f)
            # Convert timestamp from filename
            timestamp = datetime.strptime(json_path.stem.split('_')[0], '%Y%m%d_%H%M%S')
            return MarketData(**data, timestamp=timestamp)

    def update_market_history(self, currency_pair: Tuple[str, str], data: Dict):
        """Update market history for a currency pair"""
        key = f"{currency_pair[0]}_{currency_pair[1]}"
        self.market_history[key].append({
            'timestamp': datetime.now(),
            'ratio': data['market_ratio'],
            'volume': sum(trade['stock'] for trade in data['available_trades'])
        })
        
        # Keep only recent history within volatility window
        cutoff = datetime.now() - self.volatility_window
        self.market_history[key] = [
            entry for entry in self.market_history[key]
            if entry['timestamp'] > cutoff
        ]
        
        # Update known currencies
        self.known_currencies.add(currency_pair[0])
        self.known_currencies.add(currency_pair[1])

    def calculate_volatility(self, currency_pair: Tuple[str, str]) -> float:
        """Calculate price volatility for a currency pair"""
        key = f"{currency_pair[0]}_{currency_pair[1]}"
        if key not in self.market_history:
            return 0.0
            
        ratios = [float(entry['ratio'].split(':')[0]) for entry in self.market_history[key]]
        if not ratios:
            return 0.0
            
        return np.std(ratios) / np.mean(ratios)

    def find_integer_ratio_opportunities(self, market_data: MarketData) -> Optional[BasicOpportunity]:
        """Strategy 1: Find opportunities where non-integer ratios can be exploited
        Example: If market is trading at 3.37:1, buy at 3.37 and sell at 3:1
        """
        try:
            # Parse the market ratio
            ratio = float(market_data.market_ratio.split(':')[0])
            
            # Find the nearest integers
            floor_ratio = int(ratio)
            ceil_ratio = floor_ratio + 1
            
            # Calculate potential profits
            # If we can buy at floor and sell at market
            floor_profit = (ratio - floor_ratio) / floor_ratio
            # If we can buy at market and sell at ceil
            ceil_profit = (ceil_ratio - ratio) / ratio
            
            # Choose the better opportunity
            if floor_profit > ceil_profit and floor_profit > self.min_profit_threshold:
                return BasicOpportunity(
                    buy_currency=market_data.i_have,
                    sell_currency=market_data.i_want,
                    buy_ratio=f"{floor_ratio}:1",
                    sell_ratio=market_data.market_ratio,
                    potential_profit=floor_profit,
                    trade_volume=min(100, self.max_trade_volume),  # Start conservative
                    confidence=min(floor_profit * 2, 1.0)  # Higher profit = higher confidence
                )
            elif ceil_profit > self.min_profit_threshold:
                return BasicOpportunity(
                    buy_currency=market_data.i_want,
                    sell_currency=market_data.i_have,
                    buy_ratio=market_data.market_ratio,
                    sell_ratio=f"{ceil_ratio}:1",
                    potential_profit=ceil_profit,
                    trade_volume=min(100, self.max_trade_volume),
                    confidence=min(ceil_profit * 2, 1.0)
                )
        except (ValueError, IndexError):
            return None
        
        return None

    def find_spread_opportunities(self, market_data: MarketData) -> Optional[BasicOpportunity]:
        """Strategy 2: Find opportunities in the spread between available and competing trades
        Example: If someone is buying at 276:1 and selling at 274:1
        """
        if not market_data.available_trades or not market_data.competing_trades:
            return None
            
        try:
            # Get best available trade (lowest ratio when buying)
            best_available = min(
                market_data.available_trades,
                key=lambda x: float(x['ratio'].split(':')[0])
            )
            
            # Get best competing trade (highest ratio when selling)
            best_competing = max(
                market_data.competing_trades,
                key=lambda x: float(x['ratio'].split(':')[0])
            )
            
            # Calculate potential profit
            buy_ratio = float(best_available['ratio'].split(':')[0])
            sell_ratio = float(best_competing['ratio'].split(':')[0])
            
            profit_ratio = (sell_ratio - buy_ratio) / buy_ratio
            
            if profit_ratio > self.min_profit_threshold:
                # Calculate safe trade volume based on available stock
                safe_volume = min(
                    int(best_available['stock']),
                    int(best_competing['stock']),
                    self.max_trade_volume
                )
                
                return BasicOpportunity(
                    buy_currency=market_data.i_have,
                    sell_currency=market_data.i_want,
                    buy_ratio=best_available['ratio'],
                    sell_ratio=best_competing['ratio'],
                    potential_profit=profit_ratio,
                    trade_volume=safe_volume,
                    confidence=min(profit_ratio * 2, 1.0)
                )
                
        except (ValueError, KeyError):
            return None
            
        return None

    def find_triangle_arbitrage(self, market_data: Dict) -> List[TriangleOpportunity]:
        """Strategy 3: Find triangle arbitrage opportunities across currency pairs
        Example: divine -> exalt -> chaos -> divine
        """
        opportunities = []
        
        # Need at least 3 currencies for triangle arbitrage
        if len(self.known_currencies) < 3:
            return opportunities
            
        # Try all possible currency triangles
        for c1 in self.known_currencies:
            for c2 in self.known_currencies:
                if c2 == c1:
                    continue
                for c3 in self.known_currencies:
                    if c3 in (c1, c2):
                        continue
                        
                    # Get best rates for each pair
                    pairs = [(c1, c2), (c2, c3), (c3, c1)]
                    rates = []
                    volumes = []
                    
                    for base, quote in pairs:
                        key = f"{base}_{quote}"
                        if key not in self.market_history:
                            continue
                            
                        # Get latest rate and volume
                        latest = self.market_history[key][-1]
                        rates.append(float(latest['ratio'].split(':')[0]))
                        volumes.append(latest['volume'])
                    
                    if len(rates) != 3:
                        continue
                    
                    # Calculate total profit
                    total_rate = rates[0] * rates[1] * rates[2]
                    profit = total_rate - 1.0
                    
                    if profit > self.min_profit_threshold:
                        min_vol = min(volumes)
                        opportunities.append(TriangleOpportunity(
                            step1=(c1, c2, f"{rates[0]}:1"),
                            step2=(c2, c3, f"{rates[1]}:1"),
                            step3=(c3, c1, f"{rates[2]}:1"),
                            total_profit=profit,
                            min_volume=min(min_vol, self.max_trade_volume),
                            confidence=min(profit * 3, 1.0)
                        ))
        
        return sorted(opportunities, key=lambda x: x.total_profit, reverse=True)

    def find_market_making_opportunities(self, market_data: Dict) -> List[MarketMakingOpportunity]:
        """Strategy 4: Find market making opportunities based on spread and volume
        Looks for high-volume pairs with stable spreads
        """
        opportunities = []
        
        for pair_key, history in self.market_history.items():
            if len(history) < 5:  # Need some history
                continue
                
            base, quote = pair_key.split('_')
            
            # Calculate metrics
            latest = history[-1]
            current_ratio = float(latest['ratio'].split(':')[0])
            
            # Get bid-ask spread
            available_prices = [float(t['ratio'].split(':')[0]) for t in market_data['available_trades']]
            competing_prices = [float(t['ratio'].split(':')[0]) for t in market_data['competing_trades']]
            
            if not available_prices or not competing_prices:
                continue
                
            bid = min(available_prices)
            ask = max(competing_prices)
            spread = (ask - bid) / bid
            
            # Calculate volume and volatility
            volume = latest['volume']
            volatility = self.calculate_volatility((base, quote))
            
            # Score the opportunity
            # We want: High volume, Low volatility, Decent spread
            volume_score = min(volume / 1000, 1.0)  # Scale volume
            volatility_score = max(0, 1 - volatility * 10)  # Lower is better
            spread_score = min(spread * 5, 1.0)  # Higher spread is better (to a point)
            
            confidence = (volume_score + volatility_score + spread_score) / 3
            
            if confidence > 0.5:  # Only consider decent opportunities
                opportunities.append(MarketMakingOpportunity(
                    currency_pair=(base, quote),
                    bid_price=f"{bid}:1",
                    ask_price=f"{ask}:1",
                    spread=spread,
                    volume=min(volume, self.max_trade_volume),
                    volatility=volatility,
                    confidence=confidence
                ))
        
        return sorted(opportunities, key=lambda x: x.confidence, reverse=True)

    def analyze_market(self, market_data: MarketData) -> Dict[str, List]:
        """Analyze market data with all strategies"""
        opportunities = {
            'basic': [],
            'triangle': [],
            'market_making': []
        }
        
        # Basic strategies
        integer_opp = self.find_integer_ratio_opportunities(market_data)
        if integer_opp:
            opportunities['basic'].append(('Integer Arbitrage', integer_opp))
            
        spread_opp = self.find_spread_opportunities(market_data)
        if spread_opp:
            opportunities['basic'].append(('Spread Trading', spread_opp))
            
        # Advanced strategies
        triangle_opps = self.find_triangle_arbitrage(market_data)
        if triangle_opps:
            opportunities['triangle'] = triangle_opps
            
        making_opps = self.find_market_making_opportunities(market_data)
        if making_opps:
            opportunities['market_making'] = making_opps
            
        return opportunities

def main():
    # Example usage
    strategies = TradingStrategies()
    
    # Get latest market data
    market_data_dir = Path("data/market_data")
    if not market_data_dir.exists():
        print("No market data found!")
        return
        
    # Get most recent market data file
    latest_data = max(
        market_data_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime
    )
    
    # Load and analyze
    market_data = strategies.load_market_data(latest_data)
    
    # Update history
    strategies.update_market_history(
        (market_data.i_want, market_data.i_have),
        {
            'market_ratio': market_data.market_ratio,
            'available_trades': market_data.available_trades
        }
    )
    
    # Find all opportunities
    opportunities = strategies.analyze_market(market_data)
    
    # Print results
    if opportunities['basic']:
        print("\nBasic Trading Opportunities:")
        print("=" * 50)
        for strategy_name, opp in opportunities['basic']:
            print(f"\n{strategy_name}:")
            print(f"Buy {opp.buy_currency} at {opp.buy_ratio}")
            print(f"Sell {opp.sell_currency} at {opp.sell_ratio}")
            print(f"Potential Profit: {opp.potential_profit*100:.2f}%")
            print(f"Recommended Volume: {opp.trade_volume}")
            print(f"Confidence: {opp.confidence*100:.2f}%")
    
    if opportunities['triangle']:
        print("\nTriangle Arbitrage Opportunities:")
        print("=" * 50)
        for i, opp in enumerate(opportunities['triangle'], 1):
            print(f"\nOpportunity {i}:")
            print(f"Step 1: Trade {opp.step1[0]} -> {opp.step1[1]} at {opp.step1[2]}")
            print(f"Step 2: Trade {opp.step2[0]} -> {opp.step2[1]} at {opp.step2[2]}")
            print(f"Step 3: Trade {opp.step3[0]} -> {opp.step3[1]} at {opp.step3[2]}")
            print(f"Total Profit: {opp.total_profit*100:.2f}%")
            print(f"Safe Volume: {opp.min_volume}")
            print(f"Confidence: {opp.confidence*100:.2f}%")
    
    if opportunities['market_making']:
        print("\nMarket Making Opportunities:")
        print("=" * 50)
        for i, opp in enumerate(opportunities['market_making'], 1):
            print(f"\nOpportunity {i}:")
            print(f"Currency Pair: {opp.currency_pair[0]}/{opp.currency_pair[1]}")
            print(f"Bid: {opp.bid_price}, Ask: {opp.ask_price}")
            print(f"Spread: {opp.spread*100:.2f}%")
            print(f"Volume: {opp.volume}")
            print(f"Volatility: {opp.volatility*100:.2f}%")
            print(f"Confidence: {opp.confidence*100:.2f}%")

if __name__ == "__main__":
    main() 