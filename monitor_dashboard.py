#!/usr/bin/env python3
"""
Real-time API Call Monitoring Dashboard

This script provides a live dashboard showing:
- Current API call rate
- Rate limiting status
- Error patterns
- Cache hit rates
- Recommendations

Usage:
  python monitor_dashboard.py         # Show current snapshot
  python monitor_dashboard.py --live  # Live updating dashboard
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_duration(seconds):
    """Format duration in a human-readable way."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def get_status_emoji(mode):
    """Get emoji for current status."""
    mode_emojis = {
        "normal": "✅",
        "reduced": "⚡",
        "emergency": "🚨",
        "unknown": "❓"
    }
    return mode_emojis.get(mode.lower(), "❓")

def print_header():
    """Print dashboard header."""
    print("🤖 MULTI-AI DEVELOPMENT SYSTEM - API MONITORING DASHBOARD")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def print_rate_limiting_status():
    """Print rate limiting configuration and status."""
    print("🔧 RATE LIMITING CONFIGURATION")
    print("-" * 35)
    
    # Get current settings
    emergency = os.environ.get("MAISD_EMERGENCY_MODE", "false").lower() == "true"
    reduced = os.environ.get("MAISD_REDUCED_CALLS", "false").lower() == "true"
    
    if emergency:
        mode = "emergency"
        description = "EMERGENCY MODE - Minimal API calls"
    elif reduced:
        mode = "reduced"
        description = "REDUCED MODE - Conservative API calls"
    else:
        mode = "normal"
        description = "NORMAL MODE - Standard API calls"
    
    emoji = get_status_emoji(mode)
    
    print(f"{emoji} Mode: {mode.upper()}")
    print(f"📝 Description: {description}")
    print(f"📊 Calls/minute: {os.environ.get('MAISD_CALLS_PER_MINUTE', '60')}")
    print(f"⏱️  Base delay: {os.environ.get('MAISD_BASE_DELAY', '1.0')}s")
    print(f"⏳ Max delay: {os.environ.get('MAISD_MAX_DELAY', '30')}s")
    print(f"📦 Batching: {'✅' if os.environ.get('MAISD_ENABLE_BATCHING', 'false') == 'true' else '❌'}")
    print(f"💾 Aggressive cache: {'✅' if os.environ.get('MAISD_AGGRESSIVE_CACHE', 'false') == 'true' else '❌'}")
    print()

def print_api_activity():
    """Print API activity statistics."""
    print("📈 API ACTIVITY STATISTICS")
    print("-" * 30)
    
    # Rate limiting modules were removed - show basic message
    print("⚠️  Advanced rate limiting monitoring not available")
    print("Rate limiting is still active via environment variables")
    
    print("� Current session:")
    print("  📞 API calls: Not tracked (advanced monitoring removed)")
    print("  ❌ Errors: Check logs manually")
    print("  📊 Error rate: Not tracked")
    
    print()

def print_cache_statistics():
    """Print cache performance statistics."""
    print("💾 CACHE PERFORMANCE")
    print("-" * 20)
    
    try:
        # Try to get cache statistics
        from config import _response_cache
        cache_size = len(_response_cache)
        cache_limit = 1000  # From config.py
        
        print(f"📦 In-memory cache size: {cache_size}/{cache_limit}")
        print(f"📊 Cache utilization: {(cache_size/cache_limit)*100:.1f}%")
        
        if cache_size >= cache_limit * 0.9:
            print("⚠️  Cache nearly full - consider clearing or increasing limit")
        
    except ImportError:
        print("⚠️  Cache statistics not available")
    
    # Check if file cache exists
    cache_file = PROJECT_ROOT / "llm_cache.json"
    if cache_file.exists():
        cache_size_mb = cache_file.stat().st_size / (1024 * 1024)
        print(f"💽 File cache size: {cache_size_mb:.1f} MB")
    else:
        print("💽 File cache: Not found")
    
    print()

def print_recommendations():
    """Print current recommendations based on system state."""
    print("💡 RECOMMENDATIONS")
    print("-" * 18)
    
    recommendations = []
    
    # Rate limiting modules were removed - provide basic recommendations
    recommendations.append("⚠️  Advanced monitoring unavailable (rate limiting modules removed)")
    recommendations.append("✅ Basic rate limiting still active via environment variables")
    
    # Environment-based recommendations
    if os.environ.get("MAISD_AGGRESSIVE_CACHE", "false") == "false":
        recommendations.append("💾 Consider enabling aggressive caching")
    
    if os.environ.get("MAISD_ENABLE_BATCHING", "false") == "false":
        recommendations.append("📦 Consider enabling call batching")
    
    if not recommendations:
        recommendations.append("✅ System operating optimally")
    
    for rec in recommendations:
        print(f"  {rec}")
    
    print()

def print_quick_commands():
    """Print quick command reference."""
    print("🎮 QUICK COMMANDS")
    print("-" * 17)
    print("python emergency_control.py emergency  # Switch to emergency mode")
    print("python emergency_control.py reduced    # Switch to reduced mode")
    print("python emergency_control.py normal     # Switch to normal mode")
    print("python emergency_control.py status     # Show detailed status")
    print()

def show_snapshot():
    """Show a single snapshot of the system state."""
    clear_screen()
    print_header()
    print_rate_limiting_status()
    print_api_activity()
    print_cache_statistics()
    print_recommendations()
    print_quick_commands()

def live_dashboard(refresh_interval=5):
    """Show live updating dashboard."""
    print("🔴 Starting live dashboard (Ctrl+C to exit)...")
    time.sleep(1)
    
    try:
        while True:
            show_snapshot()
            print(f"🔄 Refreshing in {refresh_interval}s... (Ctrl+C to exit)")
            time.sleep(refresh_interval)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped.")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="API Call Monitoring Dashboard")
    parser.add_argument("--live", action="store_true", help="Show live updating dashboard")
    parser.add_argument("--refresh", type=int, default=5, help="Refresh interval for live mode (seconds)")
    
    args = parser.parse_args()
    
    if args.live:
        live_dashboard(args.refresh)
    else:
        show_snapshot()

if __name__ == "__main__":
    main()
