import random
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from market.strategies import TradingStrategies, MarketData
from market.market_analyzer import analyze_latest_market
from recorder import Recorder
from utils.config import CURRENCY_PAIRS

class TradingBot:
    def __init__(self):
        self.recorder = Recorder()
        self.strategies = TradingStrategies()
        self.min_liquidity = 100  # Minimum available stock
        self.min_confidence = 0.7  # Minimum confidence score
        self.scan_delay = 2  # Delay between market scans in seconds
        self.trade_cooldown = 30  # Cooldown between trades in seconds
        self.last_trade_time = datetime.min
        
    def get_random_currency_pair(self) -> Tuple[str, str]:
        """Get a random currency pair from config"""
        currencies = list(CURRENCY_PAIRS.keys())
        i_want = random.choice(currencies)
        i_have = random.choice(currencies)
        
        # Ensure we don't get the same currency
        while i_have == i_want:
            i_have = random.choice(currencies)
            
        return i_want, i_have
        
    def scan_market(self, i_want: str, i_have: str) -> Optional[MarketData]:
        """Scan market for a given currency pair"""
        try:
            # Execute market command sequence
            print(f"\nScanning market for {i_want}/{i_have}...")
            self.recorder.play_sequence("market", i_want=i_want, i_have=i_have)
            time.sleep(1)  # Wait for UI to update
            
            # Analyze the market screenshot
            market_data = analyze_latest_market()
            if not market_data:
                print("Failed to analyze market data")
                return None
                
            # Update strategies with new market data
            self.strategies.update_market_history(
                (market_data.i_want, market_data.i_have),
                {
                    'market_ratio': market_data.market_ratio,
                    'available_trades': market_data.available_trades
                }
            )
            
            return market_data
            
        except Exception as e:
            print(f"Error scanning market: {e}")
            return None
            
    def evaluate_opportunity(self, market_data: MarketData) -> bool:
        """Evaluate if a market opportunity is worth trading"""
        # Check basic liquidity
        total_volume = sum(trade.get('stock', 0) for trade in market_data.available_trades)
        if total_volume < self.min_liquidity:
            print(f"Insufficient liquidity: {total_volume} < {self.min_liquidity}")
            return False
            
        # Analyze with all strategies
        opportunities = self.strategies.analyze_market(market_data)
        
        # Check if we have any high confidence opportunities
        has_good_opportunity = False
        
        if opportunities['basic']:
            for _, opp in opportunities['basic']:
                if opp.confidence >= self.min_confidence:
                    print(f"Found basic opportunity with {opp.confidence:.2%} confidence")
                    has_good_opportunity = True
                    
        if opportunities['triangle']:
            for opp in opportunities['triangle']:
                if opp.confidence >= self.min_confidence:
                    print(f"Found triangle opportunity with {opp.confidence:.2%} confidence")
                    has_good_opportunity = True
                    
        if opportunities['market_making']:
            for opp in opportunities['market_making']:
                if opp.confidence >= self.min_confidence:
                    print(f"Found market making opportunity with {opp.confidence:.2%} confidence")
                    has_good_opportunity = True
                    
        return has_good_opportunity
        
    def execute_trade(self, market_data: MarketData):
        """Execute a trade based on market data"""
        # Check trade cooldown
        if (datetime.now() - self.last_trade_time).total_seconds() < self.trade_cooldown:
            print("Trade cooldown still active")
            return
            
        try:
            # Get trading opportunities
            opportunities = self.strategies.analyze_market(market_data)
            
            # Find best opportunity
            best_opp = None
            best_confidence = 0
            
            # Check basic opportunities
            for strategy_name, opp in opportunities['basic']:
                if opp.confidence > best_confidence:
                    best_opp = ('basic', strategy_name, opp)
                    best_confidence = opp.confidence
                    
            # Check triangle opportunities
            for opp in opportunities['triangle']:
                if opp.confidence > best_confidence:
                    best_opp = ('triangle', 'Triangle Arbitrage', opp)
                    best_confidence = opp.confidence
                    
            # Check market making opportunities
            for opp in opportunities['market_making']:
                if opp.confidence > best_confidence:
                    best_opp = ('market_making', 'Market Making', opp)
                    best_confidence = opp.confidence
                    
            if not best_opp:
                print("No suitable trading opportunities found")
                return
                
            strategy_type, strategy_name, opportunity = best_opp
            print(f"\nExecuting {strategy_name} trade...")
            
            if strategy_type == 'basic':
                # Execute basic trade
                self.recorder.play_sequence("trade", 
                    i_want=opportunity.sell_currency,
                    i_have=opportunity.buy_currency,
                    amount=str(opportunity.trade_volume)
                )
                
            elif strategy_type == 'triangle':
                # Execute triangle arbitrage
                for step in [opportunity.step1, opportunity.step2, opportunity.step3]:
                    self.recorder.play_sequence("trade",
                        i_want=step[1],
                        i_have=step[0],
                        amount=str(opportunity.min_volume)
                    )
                    time.sleep(1)  # Wait between steps
                    
            elif strategy_type == 'market_making':
                # Execute market making trade
                self.recorder.play_sequence("trade",
                    i_want=opportunity.currency_pair[1],
                    i_have=opportunity.currency_pair[0],
                    amount=str(opportunity.volume)
                )
                
            self.last_trade_time = datetime.now()
            print("Trade executed successfully")
            
        except Exception as e:
            print(f"Error executing trade: {e}")
            
    def run(self):
        """Main bot loop"""
        print("Starting trading bot...")
        
        while True:
            try:
                # Get random currency pair
                i_want, i_have = self.get_random_currency_pair()
                
                # Scan market
                market_data = self.scan_market(i_want, i_have)
                if not market_data:
                    continue
                    
                # Evaluate opportunity
                if self.evaluate_opportunity(market_data):
                    # Execute trade if opportunity is good
                    self.execute_trade(market_data)
                    
                # Wait before next scan
                time.sleep(self.scan_delay)
                
            except KeyboardInterrupt:
                print("\nStopping trading bot...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(self.scan_delay)
                
def main():
    bot = TradingBot()
    bot.run()
    
if __name__ == "__main__":
    main()