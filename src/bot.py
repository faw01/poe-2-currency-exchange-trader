import random
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import json
import pyautogui
from itertools import permutations

from .trade.strategies import TradingStrategies, MarketData
from .utils.market_gemini import analyze_latest_market
from .capture.click_recorder import ClickRecorder, get_category_for_item
from .utils.config import CURRENCY_PAIRS, CURRENCY_WEIGHTS
from .models.market_data import MarketData

class TradingBot:
    def __init__(self):
        self.recorder = ClickRecorder()
        self.strategies = TradingStrategies()
        self.min_liquidity = 100  # Minimum available stock
        self.min_confidence = 0.8  # Minimum confidence score
        self.scan_delay = 1.0  # Delay between market scans in seconds
        self.trade_cooldown = 30  # Cooldown between trades in seconds
        self.last_trade_time = datetime.min
        self.fixed_pair = None  # Fixed trading pair (currency1, currency2)
        self.last_direction = False  # False = currency1->currency2, True = currency2->currency1
        self.trade_list = None  # List of pairs to trade
        self.current_trade_list_index = 0  # Current index in trade list
        
    def get_next_pair(self) -> Tuple[str, str]:
        """Get next currency pair to trade"""
        if self.trade_list:
            # Get pair from trade list
            if self.current_trade_list_index >= len(self.trade_list):
                # Reset to beginning of list
                self.current_trade_list_index = 0
            pair = self.trade_list[self.current_trade_list_index]
            self.current_trade_list_index += 1
            return pair
        elif self.fixed_pair:
            # Only alternate direction if no opportunity was found in current direction
            if not hasattr(self, 'last_opportunity_found') or not self.last_opportunity_found:
                self.last_direction = not self.last_direction
            
            if self.last_direction:
                return self.fixed_pair[1], self.fixed_pair[0]  # Reverse direction
            return self.fixed_pair[0], self.fixed_pair[1]  # Original direction
        else:
            # Random pair selection
            items = list(CURRENCY_WEIGHTS.keys())
            weights = [CURRENCY_WEIGHTS[item] for item in items]
            
            # Get first currency with higher weight for common currencies
            i_want = random.choices(items, weights=weights, k=1)[0]
            
            # Get second currency, ensuring it's different
            while True:
                i_have = random.choices(items, weights=weights, k=1)[0]
                if i_have != i_want:
                    break
                
            return i_want, i_have
            
    def set_trade_list(self, trade_list_path: str):
        """Load currencies from file and generate all possible trading pairs"""
        try:
            # Load single currencies from file
            with open(trade_list_path) as f:
                currencies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            # Generate all possible pairs (permutations since order matters for trading)
            pairs = list(permutations(currencies, 2))
            
            self.trade_list = pairs
            print(f"\nLoaded {len(currencies)} currencies:")
            for currency in currencies:
                print(f"- {currency}")
                
            print(f"\nGenerated {len(pairs)} trading pairs:")
            for i_want, i_have in pairs:
                print(f"- {i_want} -> {i_have}")
                
        except Exception as e:
            print(f"Error loading trade list: {e}")
            self.trade_list = None
            
    def scan_market(self, i_want: str, i_have: str, current_i_want: Optional[str] = None) -> Optional[MarketData]:
        """Scan market for a given currency pair"""
        try:
            print(f"\nScanning market for {i_want}/{i_have}...")
            
            # Play i_want sequence (will skip if current_i_want matches)
            i_want_key = f"i_want_{i_want}"
            self.recorder.play_sequence(i_want_key, "select", current_i_want=current_i_want)
            
            # Always play i_have sequence
            i_have_key = f"i_have_{i_have}"
            self.recorder.play_sequence(i_have_key, "select")
            
            # Play the market sequence to capture data
            self.recorder.play_sequence("market", "market")
            time.sleep(0.2)  # Wait for UI to update
            
            # Analyze the market screenshot
            market_data = analyze_latest_market()
            if market_data:
                # Update strategies with new market data
                self.strategies.update_market_history(
                    (market_data.i_want, market_data.i_have),
                    market_data.to_dict()  # Use to_dict() to get all fields
                )
                return market_data
            else:
                print("No trades found in market data")
                return None
            
        except Exception as e:
            print(f"Error scanning market: {e}")
            return None
            
    def evaluate_opportunity(self, market_data: MarketData) -> bool:
        """Evaluate if a market opportunity is worth trading"""
        # Check basic liquidity
        total_volume = sum(trade.stock for trade in market_data.available_trades)
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
            
            # Check basic opportunities (arbitrage)
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
                # Execute arbitrage trade
                print(f"Step 1: Buy {opportunity.buy_currency} at {opportunity.buy_ratio}")
                print(f"Step 2: Sell back at {opportunity.sell_ratio}")
                print(f"Volume: {opportunity.trade_volume}")
                print(f"Expected profit: {opportunity.potential_profit*100:.2f}%")
                
                # Format currency names by replacing spaces with underscores and converting to lowercase
                i_want_currency = opportunity.buy_currency.lower().replace(' ', '_')
                i_have_currency = opportunity.sell_currency.lower().replace(' ', '_')
                
                i_want_key = f"i_want_{i_want_currency}"
                i_have_key = f"i_have_{i_have_currency}"
                
                # Step 1: Buy at the lower ratio
                print("\nExecuting buy trade...")
                
                # Navigate to the correct currencies
                self.recorder.play_sequence(i_want_key, "select")
                self.recorder.play_sequence(i_have_key, "select")
                
                # Input the amounts automatically
                buy_amount = str(int(opportunity.trade_volume))
                self.recorder.play_sequence("i_want_input", "amount", amount=buy_amount)
                
                # Calculate the have amount based on the buy ratio
                buy_ratio = self.strategies.parse_ratio(opportunity.buy_ratio)
                have_amount = str(int(float(buy_amount) * buy_ratio))
                self.recorder.play_sequence("i_have_input", "amount", amount=have_amount)
                
                # Wait before placing order
                time.sleep(0.5)
                
                # Click the trade button
                self.recorder.play_sequence("place_order", "trade")
                
                # Wait for the first trade to complete
                print("Waiting for buy trade to complete...")
                time.sleep(2)
                
                # Step 2: Sell at the higher ratio
                print("\nExecuting sell trade...")
                
                # Swap currencies (now we're selling what we just bought)
                self.recorder.play_sequence(i_have_key, "select")
                self.recorder.play_sequence(i_want_key, "select")
                
                # Input the amounts automatically (now selling what we bought)
                sell_amount = have_amount
                self.recorder.play_sequence("i_want_input", "amount", amount=sell_amount)
                
                # Calculate the receive amount based on the sell ratio
                sell_ratio = self.strategies.parse_ratio(opportunity.sell_ratio)
                receive_amount = str(int(float(sell_amount) * sell_ratio))
                self.recorder.play_sequence("i_have_input", "amount", amount=receive_amount)
                
                # Wait before placing order
                time.sleep(0.5)
                
                # Click the trade button
                self.recorder.play_sequence("place_order", "trade")
                
            elif strategy_type == 'triangle':
                # Execute triangle arbitrage
                print("Executing triangle arbitrage:")
                for i, step in enumerate([opportunity.step1, opportunity.step2, opportunity.step3], 1):
                    from_currency, to_currency, ratio = step
                    print(f"Step {i}: Trading {from_currency} -> {to_currency} at {ratio}")
                    print(f"Volume: {opportunity.min_volume}")
                    
                    # Format currency names
                    i_want_currency = to_currency.lower().replace(' ', '_')
                    i_have_currency = from_currency.lower().replace(' ', '_')
                    
                    i_want_key = f"i_want_{i_want_currency}"
                    i_have_key = f"i_have_{i_have_currency}"
                    
                    # Navigate to the correct currencies
                    self.recorder.play_sequence(i_want_key, "select")
                    self.recorder.play_sequence(i_have_key, "select")
                    
                    # Input the amounts automatically
                    want_amount = str(int(opportunity.min_volume))
                    self.recorder.play_sequence("i_want_input", "amount", amount=want_amount)
                    
                    # Calculate the have amount based on the ratio
                    step_ratio = self.strategies.parse_ratio(ratio)
                    have_amount = str(int(float(want_amount) * step_ratio))
                    self.recorder.play_sequence("i_have_input", "amount", amount=have_amount)
                    
                    # Wait before placing order
                    time.sleep(0.5)
                    
                    # Click the trade button
                    self.recorder.play_sequence("place_order", "trade")
                    
                    time.sleep(1)  # Wait between steps
                    
                print(f"Expected total profit: {opportunity.total_profit*100:.2f}%")
                
            elif strategy_type == 'market_making':
                # Execute market making trade
                base, quote = opportunity.currency_pair
                print(f"Market making for {base}/{quote}")
                print(f"Bid: {opportunity.bid_price}, Ask: {opportunity.ask_price}")
                print(f"Spread: {opportunity.spread*100:.2f}%")
                print(f"Volume: {opportunity.volume}")
                
                # Format currency names
                i_want_currency = quote.lower().replace(' ', '_')
                i_have_currency = base.lower().replace(' ', '_')
                
                i_want_key = f"i_want_{i_want_currency}"
                i_have_key = f"i_have_{i_have_currency}"
                
                # Navigate to the correct currencies
                self.recorder.play_sequence(i_want_key, "select")
                self.recorder.play_sequence(i_have_key, "select")
                
                # Input the amounts automatically
                want_amount = str(int(opportunity.volume))
                self.recorder.play_sequence("i_want_input", "amount", amount=want_amount)
                
                # Calculate the have amount based on the bid price
                bid_ratio = self.strategies.parse_ratio(opportunity.bid_price)
                have_amount = str(int(float(want_amount) * bid_ratio))
                self.recorder.play_sequence("i_have_input", "amount", amount=have_amount)
                
                # Wait before placing order
                time.sleep(0.5)
                
                # Click the trade button
                self.recorder.play_sequence("place_order", "trade")
                
            print("Trade executed successfully")
            self.last_trade_time = datetime.now()
            
            # Wait for trade cooldown
            print(f"Waiting {self.trade_cooldown} seconds before next trade...")
            time.sleep(self.trade_cooldown)
            
        except Exception as e:
            print(f"Error executing trade: {e}")
            # Wait a bit after error before retrying
            time.sleep(5)
            
    def run(self):
        """Main bot loop"""
        print("Starting trading bot...")
        self.last_opportunity_found = False
        
        # Print configuration based on mode
        if self.trade_list:
            print(f"\nTrading {len(self.trade_list)} pairs from trade list")
        elif self.fixed_pair:
            print(f"\nTrading fixed pair: {self.fixed_pair[0]} <-> {self.fixed_pair[1]}")
        else:
            print("\nTrading random pairs")
        
        print("\nBot configuration:")
        print(f"- Minimum liquidity: {self.min_liquidity}")
        print(f"- Minimum confidence: {self.min_confidence}")
        print(f"- Scan delay: {self.scan_delay}s")
        print(f"- Trade cooldown: {self.trade_cooldown}s")
        
        while True:
            try:
                # Get next currency pair
                i_want, i_have = self.get_next_pair()
                
                # Scan market
                market_data = self.scan_market(i_want, i_have)
                if not market_data:
                    print("No market data found, trying next pair...")
                    self.last_opportunity_found = False
                    time.sleep(self.scan_delay)
                    continue
                
                # Print market info
                print("\nMarket Information:")
                print("=" * 50)
                print(f"Want: {market_data.i_want}")
                print(f"Have: {market_data.i_have}")
                print(f"Market Ratio: {market_data.market_ratio}")
                print(f"Available Trades: {len(market_data.available_trades)}")
                print(f"Competing Trades: {len(market_data.competing_trades)}")
                
                # Evaluate and execute trade if opportunity exists
                if self.evaluate_opportunity(market_data):
                    print("\nGood opportunity found! Executing trade...")
                    self.last_opportunity_found = True
                    self.execute_trade(market_data)
                else:
                    print("\nNo good opportunities found, trying next pair...")
                    self.last_opportunity_found = False
                    time.sleep(self.scan_delay)
                
            except KeyboardInterrupt:
                print("\nStopping trading bot...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                self.last_opportunity_found = False
                time.sleep(self.scan_delay)
                
    def scan_market_pairs(self, pairs: List[Tuple[str, str]], output_dir: Path) -> Dict[str, Any]:
        """Scan multiple market pairs and save results"""
        total_pairs = len(pairs)
        successful_scans = 0
        failed_scans = 0
        opportunities_found = 0
        
        # Track which pairs we've already scanned (in reverse)
        scanned_pairs = set()
        
        # Sort pairs to group by i_want to minimize switching
        sorted_pairs = sorted(pairs, key=lambda x: x[0])
        
        print(f"\nStarting market scan...")
        print(f"Results will be saved in: {output_dir}")
        
        # Initialize current_i_want to None to force first i_want click
        current_i_want = None
        
        for i, (i_want, i_have) in enumerate(sorted_pairs, 1):
            # Skip if we've already scanned this pair in reverse
            pair_key = tuple(sorted([i_want, i_have]))
            if pair_key in scanned_pairs:
                print(f"\nSkipping pair {i}/{total_pairs}: {i_want} -> {i_have} (already scanned in reverse)")
                continue
                
            print(f"\nScanning pair {i}/{total_pairs}: {i_want} -> {i_have}")
            scanned_pairs.add(pair_key)
            
            try:
                # Capture and analyze market data
                market_data = self.scan_market(i_want, i_have, current_i_want)
                current_i_want = i_want  # Update current i_want after scan
                
                # Save market data
                if market_data:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    market_data_file = output_dir / f"{timestamp}_market_data.json"
                    
                    # Get opportunities and convert them to dict
                    opportunities = self.strategies.analyze_market(market_data)
                    opportunities_dict = {
                        'basic': [(name, opp.to_dict()) for name, opp in opportunities['basic']],
                        'triangle': [opp.to_dict() for opp in opportunities['triangle']],
                        'market_making': [opp.to_dict() for opp in opportunities['market_making']]
                    }
                    
                    # Save both market data and opportunities
                    data_to_save = {
                        'market_data': market_data.to_dict(),
                        'opportunities': opportunities_dict,
                        'timestamp': timestamp,
                        'pair': {'i_want': i_want, 'i_have': i_have}
                    }
                    
                    with open(market_data_file, "w") as f:
                        json.dump(data_to_save, f, indent=2)
                    
                    # Mark scan as successful if we got any market data
                    successful_scans += 1
                    
                    # Check for trading opportunities in both directions
                    if market_data.available_trades or market_data.competing_trades:
                        opportunities_found += 1
                        
                        # Just evaluate and log opportunities without executing trades
                        if self.evaluate_opportunity(market_data):
                            print("Found good trading opportunity!")
                            print(f"Want: {market_data.i_want}")
                            print(f"Have: {market_data.i_have}")
                            print(f"Market Ratio: {market_data.market_ratio}")
                            print(f"Available Trades: {len(market_data.available_trades)}")
                            print(f"Competing Trades: {len(market_data.competing_trades)}")
                    else:
                        print("No trades found in market data")
                else:
                    failed_scans += 1
                    
            except Exception as e:
                print(f"Error scanning pair: {e}")
                failed_scans += 1
                
            # Print progress
            print(f"\nProgress: {len(scanned_pairs)}/{total_pairs} pairs")
            print(f"Successful scans: {successful_scans}")
            print(f"Failed scans: {failed_scans}")
            print(f"Opportunities found: {opportunities_found}")
            
        print(f"\nMarket scan complete!")
        print(f"Total pairs scanned: {len(scanned_pairs)}/{total_pairs}")
        print(f"Successful scans: {successful_scans}")
        print(f"Failed scans: {failed_scans}")
        print(f"Opportunities found: {opportunities_found}")
        print(f"Results saved in: {output_dir}")
        
        return {
            'total_pairs': total_pairs,
            'successful_scans': successful_scans,
            'failed_scans': failed_scans,
            'opportunities_found': opportunities_found
        }

def main():
    bot = TradingBot()
    bot.run()
    
if __name__ == "__main__":
    main()