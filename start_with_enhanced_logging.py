#!/usr/bin/env python3
"""
Quick Start Script for Multi-AI Development System with Enhanced Logging
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("[AI] Starting Multi-AI Development System with Enhanced Logging")
    print("="*70)
    
    # Enable enhanced logging
    from enable_enhanced_logging import enable_enhanced_logging
    logging_system = enable_enhanced_logging()
    
    if logging_system:
        # Import and run the main system
        try:
            from main import main as run_main
            
            # Set environment variables for better logging
            os.environ["LOG_LEVEL"] = "NORMAL"
            os.environ["CONSOLE_OUTPUT"] = "true"
            os.environ["FILE_LOGGING"] = "true"
            
            print("\n[START] Starting main workflow...")
            print("[DASH] Live dashboard will be available at:")
            print(f"   {logging_system.dirs['dashboard'] / 'live_dashboard.html'}")
            print("\n" + "="*70 + "\n")
            
            # Run the main workflow
            run_main()
            
        except Exception as e:
            print(f"[ERROR] Error running main workflow: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[ERROR] Could not enable enhanced logging. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
