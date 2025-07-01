"""
Enable Enhanced Logging System for Multi-AI Development System
Run this script before starting your workflow to activate enhanced logging.
"""

import sys
import os
from pathlib import Path

def enable_enhanced_logging():
    """Enable the enhanced logging system."""
    
    print("[LOG] Enabling Enhanced Logging System...")
    
    # Import and initialize the enhanced logging system
    try:
        from enhanced_logging_system import (
            get_logging_system, 
            print_logging_info,
            get_dashboard_url
        )
        
        # Initialize the system
        system = get_logging_system()
        
        # Print setup information
        print_logging_info()
        
        # Try to patch existing monitoring
        try:
            from logging_integration_patch import patch_monitoring
            patch_monitoring()
        except ImportError:
            print("[WARN] Could not import integration patch - enhanced logging will work independently")
        
        return system
        
    except Exception as e:
        print(f"[ERROR] Failed to enable enhanced logging: {e}")
        print("Falling back to standard logging...")
        return None

def create_quick_start_script():
    """Create a quick start script that users can run."""
    
    script_content = '''#!/usr/bin/env python3
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
            
            print("\\n[START] Starting main workflow...")
            print("[DASH] Live dashboard will be available at:")
            print(f"   {logging_system.dirs['dashboard'] / 'live_dashboard.html'}")
            print("\\n" + "="*70 + "\\n")
            
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
'''
    
    with open("start_with_enhanced_logging.py", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    # Make it executable on Unix systems
    try:
        os.chmod("start_with_enhanced_logging.py", 0o755)
    except:
        pass
    
    print("[OK] Created quick start script: start_with_enhanced_logging.py")

if __name__ == "__main__":
    system = enable_enhanced_logging()
    create_quick_start_script()
    
    if system:
        print("\n🎉 Enhanced logging is now active!")
        print("\n📖 How to use:")
        print("1. Run: python start_with_enhanced_logging.py")
        print("2. Open the live dashboard in your browser")
        print("3. Monitor logs in real-time while your workflow runs")
        print("\n💡 The terminal will only show major events to keep it clean.")
        print("📁 Detailed logs are saved in organized files by category.") 