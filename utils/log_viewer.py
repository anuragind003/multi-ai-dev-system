import json
import argparse
from pathlib import Path
from datetime import datetime
from utils.log_analyzer import log_analyzer

def view_recent_api_calls(limit: int = 20):
    """Display recent API calls in a formatted way."""
    df = log_analyzer.load_api_calls()
    
    if df.empty:
        print("No API call logs found.")
        return
    
    # Sort by timestamp and get recent calls
    recent_calls = df.sort_values('timestamp', ascending=False).head(limit)
    
    print(f"\n📱 Recent {len(recent_calls)} API Calls:")
    print("=" * 100)
    
    for _, call in recent_calls.iterrows():
        status = "✅" if call['success'] else "❌"
        timestamp = call['timestamp'].strftime("%H:%M:%S")
        
        print(f"{status} [{timestamp}] {call['agent_context']} → {call['model']}")
        print(f"   Duration: {call['duration_seconds']:.2f}s | Type: {call['call_type']}")
        
        if call['temperature'] is not None:
            print(f"   Temperature: {call['temperature']}")
        
        if not call['success'] and call['error_message']:
            print(f"   Error: {call['error_message'][:100]}...")
        
        print("-" * 100)

def view_session_summary(session_id: str):
    """Display summary for a specific session."""
    summary_file = Path(f"logs/session_summary_{session_id}.json")
    
    if not summary_file.exists():
        print(f"Session summary for {session_id} not found.")
        return
    
    with open(summary_file, 'r') as f:
        summary = json.load(f)
    
    session_data = summary['session_summary']
    
    print(f"\n📊 Session Summary: {session_id}")
    print("=" * 60)
    print(f"Session Start: {session_data['session_start']}")
    print(f"Total Duration: {session_data['overall_duration_seconds']:.2f}s")
    print(f"Total API Calls: {session_data['total_api_calls']}")
    
    print(f"\nAPI Calls by Model:")
    for model, count in session_data['api_call_counts'].items():
        print(f"  - {model}: {count} calls")
    
    print(f"\nStep Durations:")
    for step, duration in session_data['step_durations_seconds'].items():
        print(f"  - {step}: {duration:.2f}s")

def main():
    parser = argparse.ArgumentParser(description="View AI system logs")
    parser.add_argument('--recent', type=int, default=20, 
                       help='Show recent API calls (default: 20)')
    parser.add_argument('--session', type=str, 
                       help='Show summary for specific session ID')
    parser.add_argument('--report', action='store_true',
                       help='Generate analysis report')
    parser.add_argument('--cleanup', type=int,
                       help='Clean up logs older than N days')
    
    args = parser.parse_args()
    
    if args.session:
        view_session_summary(args.session)
    elif args.report:
        report = log_analyzer.generate_api_report()
        report_path = log_analyzer.save_report(report)
        print(f"Analysis report saved to: {report_path}")
    elif args.cleanup:
        removed = log_analyzer.cleanup_old_logs(args.cleanup)
        print(f"Removed {len(removed)} old log files")
    else:
        view_recent_api_calls(args.recent)

if __name__ == "__main__":
    main()