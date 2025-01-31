import argparse
from pathlib import Path
import sys
from typing import Optional

from bot import TradingBot
from recorder import Recorder
from market.market_analyzer import analyze_latest_market
from market.strategies import TradingStrategies

def setup_argparse() -> argparse.ArgumentParser:
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(description='POE2 Currency Trading Bot')
    
    # Add main operation mode
    parser.add_argument('mode', choices=['bot', 'record', 'analyze', 'test'],
                       help='Operation mode: bot (run trading bot), record (record new sequences), '
                            'analyze (analyze latest market data), test (test trading strategies)')
    
    # Add optional arguments
    parser.add_argument('--sequence', '-s', type=str,
                       help='Sequence name to record (required for record mode)')
    parser.add_argument('--min-liquidity', '-l', type=int, default=100,
                       help='Minimum liquidity requirement for trading')
    parser.add_argument('--min-confidence', '-c', type=float, default=0.7,
                       help='Minimum confidence score for trading (0-1)')
    parser.add_argument('--scan-delay', '-d', type=float, default=2.0,
                       help='Delay between market scans in seconds')
    parser.add_argument('--trade-cooldown', '-t', type=int, default=30,
                       help='Cooldown between trades in seconds')
    
    return parser

def record_sequence(sequence_name: str):
    """Record a new sequence"""
    if not sequence_name:
        print("Error: Sequence name is required for record mode")
        sys.exit(1)
        
    recorder = Recorder()
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

def main():
    """Main entry point"""
    parser = setup_argparse()
    args = parser.parse_args()
    
    if args.mode == 'record':
        record_sequence(args.sequence)
    elif args.mode == 'analyze':
        analyze_market()
    elif args.mode == 'test':
        test_strategies()
    elif args.mode == 'bot':
        # Initialize and run trading bot
        bot = TradingBot()
        
        # Update bot parameters from command line
        bot.min_liquidity = args.min_liquidity
        bot.min_confidence = args.min_confidence
        bot.scan_delay = args.scan_delay
        bot.trade_cooldown = args.trade_cooldown
        
        # Run the bot
        bot.run()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main() 