#!/usr/bin/env python3
"""
Advanced Rate Limiting Utilities

Collection of utility scripts and tools for managing advanced rate limiting:
- Emergency mode activation
- Performance monitoring
- Configuration management
- Analytics and reporting
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from advanced_rate_limiting.config import get_advanced_rate_limiter
    ADVANCED_AVAILABLE = True
except ImportError:
    ADVANCED_AVAILABLE = False


class AdvancedEmergencyControl:
    """Enhanced emergency control with advanced rate limiting features."""
    
    def __init__(self):
        self.rate_limiter = get_advanced_rate_limiter() if ADVANCED_AVAILABLE else None
    
    def activate_emergency_mode(self):
        """Activate emergency mode with advanced features."""
        print("🚨 ACTIVATING ADVANCED EMERGENCY MODE 🚨")
        
        if not ADVANCED_AVAILABLE:
            print("⚠️  Advanced rate limiting not available, using basic mode")
            self._activate_basic_emergency()
            return
        
        # Set advanced emergency mode
        self.rate_limiter.set_mode('emergency')
        
        # Configure environment variables
        env_vars = {
            "MAISD_ENABLE_ADVANCED_RATE_LIMITING": "true",
            "MAISD_ENABLE_INTELLIGENT_CACHING": "true",
            "MAISD_ENABLE_REQUEST_DEDUPLICATION": "true",
            "MAISD_ENABLE_SMART_RETRIES": "true",
            "MAISD_ENABLE_AUTO_ESCALATION": "true",
            "MAISD_EMERGENCY_MODE": "true",
            "MAISD_CALLS_PER_MINUTE": "5",
            "MAISD_BASE_DELAY": "10.0",
            "MAISD_MAX_DELAY": "300"
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            print(f"✅ Set {key}={value}")
        
        print("\n🔥 ADVANCED EMERGENCY MODE ACTIVE:")
        print("  - Ultra-conservative rate limiting (5 calls/min)")
        print("  - Maximum delays up to 5 minutes")
        print("  - Intelligent caching enabled")
        print("  - Request deduplication active")
        print("  - Smart retry strategies enabled")
        print("  - Auto-escalation monitoring active")
    
    def _activate_basic_emergency(self):
        """Fallback to basic emergency mode."""
        env_vars = {
            "MAISD_EMERGENCY_MODE": "true",
            "MAISD_CALLS_PER_MINUTE": "5",
            "MAISD_BASE_DELAY": "10.0",
            "MAISD_MAX_DELAY": "300"
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
            print(f"✅ Set {key}={value}")
    
    def show_advanced_stats(self):
        """Show comprehensive advanced statistics."""
        print("📈 ADVANCED RATE LIMITING STATISTICS")
        print("=" * 50)
        
        if not ADVANCED_AVAILABLE:
            print("⚠️  Advanced rate limiting not available")
            return
        
        try:
            stats = self.rate_limiter.get_comprehensive_stats()
            
            if not stats.get('enabled', False):
                print("⚠️  Advanced rate limiting is disabled")
                return
            
            # Rate limiting stats
            if 'rate_limiting' in stats:
                rl_stats = stats['rate_limiting']
                print("🚦 Rate Limiting Status:")
                print(f"  Current mode: {rl_stats.get('current_mode', 'unknown').upper()}")
                print(f"  Mode duration: {rl_stats.get('mode_duration_minutes', 0):.1f} minutes")
                print(f"  Calls in last minute: {rl_stats.get('current_calls_per_minute', 0)}")
                print(f"  Last call: {rl_stats.get('last_call_seconds_ago', 'never')} seconds ago")
            
            # API tracking stats
            if 'api_tracking' in stats:
                api_stats = stats['api_tracking']
                
                print("\n📊 API Activity (Last 15 minutes):")
                stats_15 = api_stats.get('stats_15min', {})
                print(f"  Total calls: {stats_15.get('total_calls', 0)}")
                print(f"  Total errors: {stats_15.get('total_errors', 0)}")
                print(f"  Error rate: {stats_15.get('error_rate', 0):.1f}%")
                print(f"  Avg response time: {stats_15.get('avg_response_time', 0):.2f}s")
                print(f"  Performance trend: {stats_15.get('performance_trend', 'unknown')}")
                
                print("\n📊 API Activity (Last 1 hour):")
                stats_60 = api_stats.get('stats_1hour', {})
                print(f"  Total calls: {stats_60.get('total_calls', 0)}")
                print(f"  Total errors: {stats_60.get('total_errors', 0)}")
                print(f"  Error rate: {stats_60.get('error_rate', 0):.1f}%")
            
            # Optimization stats
            if 'optimization' in stats:
                opt_stats = stats['optimization']
                
                print("\n⚡ Optimization Performance:")
                cache_stats = opt_stats.get('cache', {})
                print(f"  Cache hit rate: {cache_stats.get('hit_rate', 0):.1f}%")
                print(f"  Cache entries: {cache_stats.get('total_entries', 0)}")
                print(f"  Cache size: {cache_stats.get('total_size_mb', 0):.1f} MB")
                
                optimization = opt_stats.get('optimization', {})
                print(f"  API calls saved by cache: {optimization.get('cache_saves', 0)}")
                print(f"  API calls saved by deduplication: {optimization.get('dedup_saves', 0)}")
                print(f"  Successful retries: {optimization.get('successful_retries', 0)}")
                print(f"  Retry success rate: {opt_stats.get('retry_success_rate', 0):.1f}%")
            
            # Recommendations
            self._show_recommendations(stats)
            
        except Exception as e:
            print(f"❌ Error getting advanced stats: {e}")
    
    def _show_recommendations(self, stats: Dict[str, Any]):
        """Show intelligent recommendations based on stats."""
        print("\n💡 INTELLIGENT RECOMMENDATIONS:")
        
        api_stats = stats.get('api_tracking', {})
        stats_15 = api_stats.get('stats_15min', {})
        
        error_rate = stats_15.get('error_rate', 0)
        total_errors = stats_15.get('total_errors', 0)
        performance_trend = stats_15.get('performance_trend', 'stable')
        
        if error_rate > 20:
            print("🚨 CRITICAL: Very high error rate - consider EMERGENCY mode")
        elif error_rate > 10:
            print("⚠️  WARNING: Elevated error rate - consider REDUCED mode")
        elif error_rate > 5:
            print("⚡ NOTICE: Moderate error rate - monitor closely")
        else:
            print("✅ GOOD: Error rate is acceptable")
        
        if performance_trend == 'degrading':
            print("📉 TREND: Performance is degrading - consider reducing load")
        elif performance_trend == 'improving':
            print("📈 TREND: Performance is improving - current settings working well")
        
        # Cache recommendations
        opt_stats = stats.get('optimization', {})
        if opt_stats:
            cache_stats = opt_stats.get('cache', {})
            hit_rate = cache_stats.get('hit_rate', 0)
            
            if hit_rate < 30:
                print("💾 CACHE: Low hit rate - consider adjusting cache size or contexts")
            elif hit_rate > 80:
                print("💾 CACHE: Excellent hit rate - cache is very effective")
    
    def export_analytics(self, output_file: str = None):
        """Export detailed analytics to file."""
        if not ADVANCED_AVAILABLE:
            print("⚠️  Advanced analytics not available")
            return
        
        try:
            analytics = self.rate_limiter.export_analytics()
            
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"advanced_analytics_{timestamp}.json"
            
            with open(output_file, 'w') as f:
                json.dump(analytics, f, indent=2, default=str)
            
            print(f"📊 Analytics exported to: {output_file}")
            
        except Exception as e:
            print(f"❌ Error exporting analytics: {e}")


def main():
    """Main CLI interface for advanced rate limiting utilities."""
    parser = argparse.ArgumentParser(description="Advanced Rate Limiting Utilities")
    parser.add_argument('command', choices=['emergency', 'reduced', 'normal', 'status', 'stats', 'analytics'],
                       help='Command to execute')
    parser.add_argument('--output', '-o', help='Output file for analytics export')
    
    args = parser.parse_args()
    
    control = AdvancedEmergencyControl()
    
    if args.command == 'emergency':
        control.activate_emergency_mode()
    elif args.command == 'reduced':
        print("⚡ Activating REDUCED mode with advanced features...")
        if ADVANCED_AVAILABLE:
            control.rate_limiter.set_mode('reduced')
        print("⚡ REDUCED mode activated")
    elif args.command == 'normal':
        print("🎉 Returning to NORMAL mode...")
        if ADVANCED_AVAILABLE:
            control.rate_limiter.set_mode('normal')
        print("🎉 NORMAL mode activated")
    elif args.command == 'status':
        control.show_advanced_stats()
    elif args.command == 'stats':
        control.show_advanced_stats()
    elif args.command == 'analytics':
        control.export_analytics(args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
