from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import numpy as np
from collections import defaultdict
from ..models.market_data import MarketData, Trade

@dataclass
class TradingOpportunity:
    buy_currency: str
    sell_currency: str
    buy_ratio: str
    sell_ratio: str
    potential_profit: float
    trade_volume: int
    confidence: float

    def to_dict(self):
        return {
            'buy_currency': self.buy_currency,
            'sell_currency': self.sell_currency,
            'buy_ratio': self.buy_ratio,
            'sell_ratio': self.sell_ratio,
            'potential_profit': self.potential_profit,
            'trade_volume': self.trade_volume,
            'confidence': self.confidence
        }

@dataclass
class TriangleOpportunity:
    step1: Tuple[str, str, str]  # (from_currency, to_currency, ratio)
    step2: Tuple[str, str, str]
    step3: Tuple[str, str, str]
    total_profit: float
    min_volume: int
    confidence: float

    def to_dict(self):
        return {
            'step1': list(self.step1),
            'step2': list(self.step2),
            'step3': list(self.step3),
            'total_profit': self.total_profit,
            'min_volume': self.min_volume,
            'confidence': self.confidence
        }

@dataclass
class MarketMakingOpportunity:
    currency_pair: Tuple[str, str]  # (base, quote)
    bid_price: str
    ask_price: str
    spread: float
    volume: int
    volatility: float
    confidence: float

    def to_dict(self):
        return {
            'currency_pair': list(self.currency_pair),
            'bid_price': self.bid_price,
            'ask_price': self.ask_price,
            'spread': self.spread,
            'volume': self.volume,
            'volatility': self.volatility,
            'confidence': self.confidence
        }

class TradingStrategies:
    def __init__(self):
        self.market_history = {}
        self.history_window = timedelta(minutes=30)
        self.min_profit_threshold = 0.015  # 1.5% minimum profit
        self.max_trade_volume = 1000
        self.volatility_window = timedelta(minutes=30)
        self.known_currencies: Set[str] = set()

    def parse_ratio(self, ratio_str: str) -> float:
        """Parse a ratio string into a float value"""
        try:
            # Handle "x:y" format
            if ':' in ratio_str:
                num, denom = ratio_str.split(':')
                # Remove any non-numeric characters
                num = ''.join(c for c in num if c.isdigit() or c == '.')
                denom = ''.join(c for c in denom if c.isdigit() or c == '.')
                if not num or not denom:
                    return 0.0
                return float(num) / float(denom)
            
            # Handle "<x:y" or ">x:y" format
            if ratio_str.startswith(('<', '>')):
                base_ratio = ratio_str[1:].strip()
                return self.parse_ratio(base_ratio)
            
            # If just a number, return it
            if ratio_str.replace('.', '').isdigit():
                return float(ratio_str)
            
            return 0.0
        except (ValueError, ZeroDivisionError):
            return 0.0

    def load_market_data(self, json_path: Path) -> MarketData:
        """Load market data from JSON file"""
        with open(json_path) as f:
            data = json.load(f)
            # Convert timestamp from filename
            timestamp = datetime.strptime(json_path.stem.split('_')[0], '%Y%m%d_%H%M%S')
            return MarketData(**data, timestamp=timestamp)

    def update_market_history(self, pair: Tuple[str, str], data: Dict):
        """Update market history with new data"""
        now = datetime.now()
        
        # Convert Trade objects to dictionaries if needed
        if isinstance(data.get('available_trades', []), list):
            data['available_trades'] = [
                t.to_dict() if isinstance(t, Trade) else t 
                for t in data['available_trades']
            ]
        if isinstance(data.get('competing_trades', []), list):
            data['competing_trades'] = [
                t.to_dict() if isinstance(t, Trade) else t 
                for t in data['competing_trades']
            ]
        
        self.market_history[pair] = {
            'timestamp': now,
            'data': data
        }
        
        # Clean old history
        cutoff = now - self.history_window
        self.market_history = {
            k: v for k, v in self.market_history.items()
            if v['timestamp'] > cutoff
        }
        
        # Update known currencies
        self.known_currencies.add(pair[0])
        self.known_currencies.add(pair[1])

    def calculate_volatility(self, currency_pair: Tuple[str, str]) -> float:
        """Calculate price volatility for a currency pair"""
        if currency_pair not in self.market_history:
            return 0.0
        
        try:
            ratios = [self.parse_ratio(entry['ratio']) for entry in self.market_history[currency_pair]['data']['available_trades']]
            if not ratios:
                return 0.0
            
            # Filter out invalid ratios
            ratios = [r for r in ratios if r > 0]
            if not ratios:
                return 0.0
            
            return np.std(ratios) / np.mean(ratios)
        except (KeyError, ValueError, ZeroDivisionError):
            return 0.0

    def find_integer_ratio_opportunities(self, market_data: MarketData) -> Optional[TradingOpportunity]:
        """Find opportunities where ratios are clean integers"""
        try:
            # Check available trades
            for trade in market_data.available_trades:
                ratio = self.parse_ratio(trade.ratio)
                if ratio > 0:  # Valid ratio
                    # Check if either numerator or denominator is an integer
                    if ratio.is_integer() or (1/ratio).is_integer():
                        # Found potential integer ratio trade
                        return TradingOpportunity(
                            buy_currency=market_data.i_want,
                            sell_currency=market_data.i_have,
                            buy_ratio=trade.ratio,
                            sell_ratio=market_data.market_ratio,
                            potential_profit=0.05,  # 5% estimated profit
                            trade_volume=min(100, trade.stock),  # Conservative volume
                            confidence=0.8
                        )
        except (ValueError, ZeroDivisionError):
            pass
        
        return None
        
    def find_spread_opportunities(self, market_data: MarketData) -> Optional[TradingOpportunity]:
        """Find opportunities with significant spreads"""
        if not market_data.available_trades or not market_data.competing_trades:
            return None
            
        # Get best available and competing trades
        try:
            best_available = market_data.available_trades[0]
            best_competing = market_data.competing_trades[0]
            
            # Convert ratios to floats for comparison
            avail_ratio = self.parse_ratio(best_available.ratio)
            comp_ratio = self.parse_ratio(best_competing.ratio)
            
            if avail_ratio > 0 and comp_ratio > 0:  # Only consider valid ratios
                # Calculate spread
                spread = abs(avail_ratio - comp_ratio) / min(avail_ratio, comp_ratio)
                
                if spread > 0.05:  # 5% spread threshold
                    return TradingOpportunity(
                        buy_currency=market_data.i_want,
                        sell_currency=market_data.i_have,
                        buy_ratio=best_available.ratio,
                        sell_ratio=best_competing.ratio,
                        potential_profit=spread,
                        trade_volume=min(100, best_available.stock),
                        confidence=min(0.9, spread * 10)  # Higher spread = higher confidence
                    )
        except (ValueError, IndexError, ZeroDivisionError):
            pass
            
        return None

    def find_triangle_arbitrage(self, market_data: MarketData) -> List[TriangleOpportunity]:
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
                        key = (base, quote)  # Use tuple directly as key
                        if key not in self.market_history:
                            continue
                            
                        # Get latest rate and volume
                        latest = self.market_history[key]['data']
                        if not latest['available_trades']:
                            continue
                            
                        # Use first trade for rate and volume
                        first_trade = latest['available_trades'][0]
                        rate = self.parse_ratio(first_trade['ratio'])
                        if rate <= 0:  # Skip invalid rates
                            continue
                            
                        rates.append(rate)
                        volumes.append(first_trade['stock'])
                    
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

    def find_market_making_opportunities(self, market_data: MarketData) -> List[MarketMakingOpportunity]:
        """Strategy 4: Find market making opportunities based on spread and volume
        Looks for high-volume pairs with stable spreads
        """
        opportunities = []
        
        for pair_key, history in self.market_history.items():
            try:
                if not history['data']['available_trades'] or not history['data']['competing_trades']:
                    continue
                
                base, quote = pair_key  # Unpack tuple directly
                
                # Calculate metrics
                latest = history['data']['available_trades'][0]  # Use first trade instead of last
                current_ratio = self.parse_ratio(latest['ratio'])
                
                # Get bid-ask spread
                available_prices = [self.parse_ratio(t['ratio']) for t in history['data']['available_trades']]
                competing_prices = [self.parse_ratio(t['ratio']) for t in history['data']['competing_trades']]
                
                if not available_prices or not competing_prices:
                    continue
                
                bid = min(available_prices)
                ask = max(competing_prices)
                if bid <= 0 or ask <= 0:  # Skip invalid prices
                    continue
                
                spread = (ask - bid) / bid
                volume = latest['stock']
                volatility = self.calculate_volatility(pair_key)  # Pass tuple directly
                
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
                        volume=volume,
                        volatility=volatility,
                        confidence=confidence
                    ))
            except (KeyError, IndexError, ValueError):
                continue  # Skip any errors in market making analysis
        
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
            opportunities['basic'].append(('Integer Ratio', integer_opp))
            
        spread_opp = self.find_spread_opportunities(market_data)
        if spread_opp:
            opportunities['basic'].append(('Spread', spread_opp))
            
        # Advanced strategies
        triangle_opps = self.find_triangle_arbitrage(market_data)
        if triangle_opps:
            opportunities['triangle'] = triangle_opps
            
        making_opps = self.find_market_making_opportunities(market_data)
        if making_opps:
            opportunities['market_making'] = making_opps
            
        return opportunities

    def analyze_basic_opportunities(self, market_data: MarketData) -> List[Tuple[str, TradingOpportunity]]:
        """Analyze basic trading opportunities"""
        opportunities = []
        
        if not market_data.available_trades or not market_data.competing_trades:
            return opportunities
        
        # Get best available trade (lowest ratio for buying)
        best_available = None
        best_available_ratio = float('inf')
        
        for trade in market_data.available_trades:
            ratio = self.parse_ratio(trade['ratio'])
            if ratio > 0 and ratio < best_available_ratio:
                best_available = trade
                best_available_ratio = ratio
            
        # Get best competing trade (highest ratio for selling)
        best_competing = None
        best_competing_ratio = 0
        
        for trade in market_data.competing_trades:
            ratio = self.parse_ratio(trade['ratio'])
            if ratio > best_competing_ratio:
                best_competing = trade
                best_competing_ratio = ratio
            
        if not best_available or not best_competing:
            return opportunities
        
        # Calculate potential arbitrage
        if best_competing_ratio > best_available_ratio:
            profit_ratio = (best_competing_ratio - best_available_ratio) / best_available_ratio
            
            # Cap trade volume at 100 for safety
            volume = min(int(best_available['stock']), 100) if isinstance(best_available['stock'], (int, float)) else 100
            
            opportunity = TradingOpportunity(
                strategy_name="Basic Arbitrage",
                buy_currency=market_data.i_want,
                sell_currency=market_data.i_have,
                buy_ratio=str(best_available_ratio),
                sell_ratio=str(best_competing_ratio),
                trade_volume=volume,
                potential_profit=profit_ratio,
                confidence=min(1.0, profit_ratio * 2)  # Scale confidence with profit
            )
            
            opportunities.append(("Basic Arbitrage", opportunity))
            
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