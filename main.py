import argparse
from pathlib import Path
import sys
from typing import Optional
import time
from datetime import datetime

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

from src.bot import TradingBot
from src.capture.click_recorder import ClickRecorder, get_category_for_item
from src.utils.market_gemini import analyze_latest_market
from src.trade.strategies import TradingStrategies

def setup_argparse() -> argparse.ArgumentParser:
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(description='POE2 Currency Trading Bot')
    
    # Add main operation mode
    parser.add_argument('mode', choices=['bot', 'record', 'analyze', 'test', 'scan'],
                       help='Operation mode: bot (run trading bot), record (record new sequences), '
                            'analyze (analyze latest market data), test (test trading strategies), '
                            'scan (scan entire market for all pairs)')
    
    # Add optional arguments
    parser.add_argument('--sequence', '-s', type=str,
                       help='Sequence name to record (required for record mode)')
    parser.add_argument('--want', '-w', type=str,
                       help='Currency to buy (e.g., chaos_orb)')
    parser.add_argument('--have', '-v', type=str,
                       help='Currency to sell (e.g., divine_orb)')
    parser.add_argument('--min-liquidity', '-l', type=int, default=100,
                       help='Minimum liquidity requirement for trading')
    parser.add_argument('--min-confidence', '-c', type=float, default=0.7,
                       help='Minimum confidence score for trading (0-1)')
    parser.add_argument('--scan-delay', '-d', type=float, default=2.0,
                       help='Delay between market scans in seconds')
    parser.add_argument('--trade-cooldown', '-t', type=int, default=30,
                       help='Cooldown between trades in seconds')
    parser.add_argument('--max-pairs', '-m', type=int,
                       help='Maximum number of pairs to scan (for scan mode)')
    parser.add_argument('--category', type=str,
                       help='Specific category to scan (for scan mode)')
    parser.add_argument('--trade-list', type=str,
                       help='Path to file containing list of items to scan for trading opportunities')
    
    return parser

def record_sequence(sequence_name: str):
    """Record a new sequence"""
    if not sequence_name:
        print("Error: Sequence name is required for record mode")
        sys.exit(1)
        
    recorder = ClickRecorder()
    print(f"\nRecording new sequence: {sequence_name}")
    print("Press Ctrl+C to stop recording")
    
    try:
        recorder.record_sequence(sequence_name)
    except KeyboardInterrupt:
        print("\nRecording stopped")
    except Exception as e:
        print(f"Error recording sequence: {e}")
        sys.exit(1)

def analyze_market():
    """Analyze latest market data"""
    try:
        print("\nAnalyzing latest market data...")
        market_data = analyze_latest_market()
        
        if not market_data:
            print("No market data found to analyze")
            return
            
        # Initialize strategies and analyze
        strategies = TradingStrategies()
        opportunities = strategies.analyze_market(market_data)
        
        # Print market info
        print("\nMarket Information:")
        print("=" * 50)
        print(f"Want: {market_data.i_want}")
        print(f"Have: {market_data.i_have}")
        print(f"Market Ratio: {market_data.market_ratio}")
        print(f"Available Trades: {len(market_data.available_trades)}")
        print(f"Competing Trades: {len(market_data.competing_trades)}")
        
        # Print opportunities
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
                
    except Exception as e:
        print(f"Error analyzing market: {e}")
        sys.exit(1)

def test_strategies():
    """Test trading strategies with historical data"""
    try:
        print("\nTesting trading strategies...")
        
        # Get all market data files
        market_data_dir = Path("data/market_data")
        if not market_data_dir.exists():
            print("No market data found for testing")
            return
            
        # Initialize strategies
        strategies = TradingStrategies()
        
        # Load and analyze each file
        for data_file in sorted(market_data_dir.glob("*.json")):
            print(f"\nAnalyzing {data_file.name}...")
            
            # Load market data
            market_data = strategies.load_market_data(data_file)
            
            # Update history
            strategies.update_market_history(
                (market_data.i_want, market_data.i_have),
                {
                    'market_ratio': market_data.market_ratio,
                    'available_trades': market_data.available_trades
                }
            )
            
            # Analyze opportunities
            opportunities = strategies.analyze_market(market_data)
            
            # Print summary
            total_opps = (
                len(opportunities['basic']) +
                len(opportunities['triangle']) +
                len(opportunities['market_making'])
            )
            print(f"Found {total_opps} potential opportunities")
            
    except Exception as e:
        print(f"Error testing strategies: {e}")
        sys.exit(1)

def scan_market_pairs(args: argparse.Namespace):
    """Scan the entire market for all possible currency pairs"""
    from itertools import combinations
    from src.utils.config import load_tradeables
    import random
    
    print("\nInitializing market scanner...")
    
    # Initialize bot for scanning
    bot = TradingBot()
    
    # Update bot parameters from command line
    bot.scan_delay = args.scan_delay
    
    # Load all tradeable items
    tradeables = load_tradeables()
    print(f"Loaded {len(tradeables)} tradeable items")
    
    # Generate all possible pairs (only one direction)
    pairs = list(combinations(sorted(tradeables), 2))
    print(f"Generated {len(pairs)} possible pairs")
    
    # If max_pairs specified, randomly sample pairs
    if args.max_pairs and args.max_pairs < len(pairs):
        pairs = random.sample(pairs, args.max_pairs)
        print(f"Randomly selected {args.max_pairs} pairs to scan")
    
    # Create results directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(f"data/market_scans/{timestamp}")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    print("\nStarting market scan...")
    print(f"Results will be saved in: {results_dir}")
    
    total_pairs = len(pairs)
    successful_scans = 0
    failed_scans = 0
    
    for i, (currency1, currency2) in enumerate(pairs, 1):
        print(f"\nScanning pair {i}/{total_pairs}: {currency1} <-> {currency2}")
        
        try:
            # Scan in one direction only - we'll get both directions' data
            market_data = bot.scan_market(currency1, currency2)
            if market_data:
                successful_scans += 1
                # The reverse direction data is in competing_trades
            else:
                failed_scans += 1
                
            # Add delay between pairs
            time.sleep(bot.scan_delay)
            
        except KeyboardInterrupt:
            print("\nScan interrupted by user")
            break
        except Exception as e:
            print(f"Error scanning pair: {e}")
            failed_scans += 1
            
        # Print progress
        print(f"\nProgress: {i}/{total_pairs} pairs")
        print(f"Successful scans: {successful_scans}")
        print(f"Failed scans: {failed_scans}")
    
    print("\nMarket scan complete!")
    print(f"Total pairs scanned: {i}/{total_pairs}")
    print(f"Successful scans: {successful_scans}")
    print(f"Failed scans: {failed_scans}")
    print(f"Results saved in: {results_dir}")

def scan_trade_list(args: argparse.Namespace):
    """Scan market for trading opportunities among specified items"""
    from itertools import combinations
    from datetime import datetime
    import json
    
    print("\nInitializing trade list scanner...")
    
    # Initialize bot for scanning
    bot = TradingBot()
    bot.scan_delay = args.scan_delay
    bot.min_liquidity = args.min_liquidity
    bot.min_confidence = args.min_confidence
    
    # Load trade list
    try:
        with open(args.trade_list) as f:
            trade_items = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(trade_items)} items from trade list")
    except Exception as e:
        print(f"Error loading trade list: {e}")
        return
    
    # Generate all possible pairs (only one direction)
    pairs = list(combinations(sorted(trade_items), 2))
    print(f"Generated {len(pairs)} possible trading pairs")
    
    # Create results directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(f"data/trade_scans/{timestamp}")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Create opportunities file
    opportunities_file = results_dir / "opportunities.json"
    opportunities = []
    
    print("\nStarting trade scan...")
    print(f"Results will be saved in: {results_dir}")
    
    total_pairs = len(pairs)
    successful_scans = 0
    failed_scans = 0
    opportunities_found = 0
    
    for i, (currency1, currency2) in enumerate(pairs, 1):
        print(f"\nScanning pair {i}/{total_pairs}: {currency1} -> {currency2}")
        
        try:
            # Scan market in one direction
            market_data = bot.scan_market(currency1, currency2)
            if market_data:
                successful_scans += 1
                
                # Check opportunities in both directions
                # Forward direction
                if bot.evaluate_opportunity(market_data):
                    opportunities_found += 1
                    opportunities.append({
                        "timestamp": datetime.now().isoformat(),
                        "pair": [currency1, currency2],
                        "direction": "forward",
                        "market_data": market_data.to_dict()
                    })
                
                # Reverse direction (using competing_trades)
                # Note: You might want to create a reversed MarketData object here
                # if your evaluation logic needs it in a specific format
                
                # Save opportunities after each find
                if opportunities:
                    with open(opportunities_file, 'w') as f:
                        json.dump(opportunities, f, indent=2)
            else:
                failed_scans += 1
                
            # Add delay between pairs
            time.sleep(bot.scan_delay)
            
        except KeyboardInterrupt:
            print("\nScan interrupted by user")
            break
        except Exception as e:
            print(f"Error scanning pair: {e}")
            failed_scans += 1
            
        # Print progress
        print(f"\nProgress: {i}/{total_pairs} pairs")
        print(f"Successful scans: {successful_scans}")
        print(f"Failed scans: {failed_scans}")
        print(f"Opportunities found: {opportunities_found}")
    
    print("\nTrade scan complete!")
    print(f"Total pairs scanned: {i}/{total_pairs}")
    print(f"Successful scans: {successful_scans}")
    print(f"Failed scans: {failed_scans}")
    print(f"Opportunities found: {opportunities_found}")
    print(f"Results saved in: {results_dir}")

def main():
    """Main entry point"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    print("Starting POE2 Currency Trading Bot...")
    
    if args.mode == 'record':
        if args.want and args.have:
            # Record sequences for specific trading pair
            print(f"\nRecording sequences for trading {args.want} -> {args.have}")
            recorder = ClickRecorder()
            
            # Record i_want sequence
            i_want_key = f"i_want_{args.want}"
            print(f"\nRecording sequence: {i_want_key}")
            print("Press Ctrl+C to stop recording")
            try:
                recorder.record_sequence(i_want_key)
            except KeyboardInterrupt:
                print("\nRecording stopped")
            
            # Record i_have sequence
            i_have_key = f"i_have_{args.have}"
            print(f"\nRecording sequence: {i_have_key}")
            print("Press Ctrl+C to stop recording")
            try:
                recorder.record_sequence(i_have_key)
            except KeyboardInterrupt:
                print("\nRecording stopped")
            
            # Record market sequence if it doesn't exist
            if "market" not in recorder.sequences:
                print("\nRecording market sequence")
                print("Press Ctrl+C to stop recording")
                try:
                    recorder.record_sequence("market")
                except KeyboardInterrupt:
                    print("\nRecording stopped")
        else:
            record_sequence(args.sequence)
    elif args.mode == 'analyze':
        analyze_market()
    elif args.mode == 'test':
        test_strategies()
    elif args.mode == 'scan':
        if args.trade_list:
            scan_trade_list(args)
        else:
            scan_market_pairs(args)
    elif args.mode == 'bot':
        # Initialize and run trading bot
        print("Initializing trading bot...")
        bot = TradingBot()
        
        # Update bot parameters from command line
        bot.min_liquidity = args.min_liquidity
        bot.min_confidence = args.min_confidence
        bot.scan_delay = args.scan_delay
        bot.trade_cooldown = args.trade_cooldown
        
        # Set trading mode based on arguments
        if args.trade_list:
            bot.set_trade_list(args.trade_list)
        elif args.want and args.have:
            bot.fixed_pair = (args.want, args.have)
            print(f"\nTrading pair: {args.want} <-> {args.have}")
            print("(Will alternate between both directions)")
        else:
            bot.fixed_pair = None
            print("\nTrading random pairs")
        
        print(f"\nBot configuration:")
        print(f"- Minimum liquidity: {bot.min_liquidity}")
        print(f"- Minimum confidence: {bot.min_confidence}")
        print(f"- Scan delay: {bot.scan_delay}s")
        print(f"- Trade cooldown: {bot.trade_cooldown}s")
        
        # Run the bot
        print("\nStarting bot operation...")
        bot.run()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
