from time import sleep
from typing import List
from screen_capture.capture import ScreenCapture
from strategies.base import BaseStrategy

class TradingBot:
    def __init__(self, screen_capture: ScreenCapture, strategies: List[BaseStrategy]):
        self.screen_capture = screen_capture
        self.strategies = strategies
        self.running = False
        
    def start(self, check_interval: float = 2.0):
        """Start the trading bot"""
        self.running = True
        print("Bot started... Press Ctrl+C to stop")
        
        while self.running:
            try:
                # Get current rates
                rates = self.screen_capture.get_exchange_rates()
                
                # Check each strategy for opportunities
                for strategy in self.strategies:
                    opportunity = strategy.analyze_opportunity(rates)
                    if opportunity:
                        success = strategy.execute_trade(opportunity)
                        if success:
                            print(f"Trade executed: {opportunity}")
                
                # Wait before next check
                sleep(check_interval)
                
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                print(f"Error in main loop: {e}")
                sleep(check_interval)
                
    def stop(self):
        """Stop the trading bot"""
        self.running = False
        print("\nBot stopped")
        
        # Print final stats
        for i, strategy in enumerate(self.strategies):
            stats = strategy.get_stats()
            print(f"\nStrategy {i+1} stats:")
            print(f"Total trades: {stats['trades']}")
            print(f"Total profit: {stats['profit']}")
            if stats['trades'] > 0:
                print(f"Average profit: {stats['avg_profit']:.2%}")