import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import seaborn as sns

class LogAnalyzer:
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.api_logs_dir = self.logs_dir / "api_calls"
        self.agent_logs_dir = self.logs_dir / "agent_activity"
        self.workflow_logs_dir = self.logs_dir / "workflow"

    def load_api_calls(self, date: Optional[str] = None, session_id: Optional[str] = None) -> pd.DataFrame:
        """Load API calls from log files."""
        api_calls = []
        
        if session_id:
            # Load specific session
            session_file = self.api_logs_dir / f"session_{session_id}_api_calls.jsonl"
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        api_calls.append(json.loads(line.strip()))
        elif date:
            # Load specific date
            daily_file = self.api_logs_dir / f"api_calls_{date}.jsonl"
            if daily_file.exists():
                with open(daily_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        api_calls.append(json.loads(line.strip()))
        else:
            # Load all recent files
            for log_file in self.api_logs_dir.glob("api_calls_*.jsonl"):
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        api_calls.append(json.loads(line.strip()))
        
        if not api_calls:
            return pd.DataFrame()
        
        df = pd.DataFrame(api_calls)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    def generate_api_report(self, session_id: Optional[str] = None) -> Dict:
        """Generate comprehensive API usage report."""
        df = self.load_api_calls(session_id=session_id)
        
        if df.empty:
            return {"error": "No API call data found"}
        
        report = {
            "summary": {
                "total_calls": len(df),
                "unique_models": df['model'].nunique(),
                "unique_agents": df['agent_context'].nunique(),
                "total_duration": df['duration_seconds'].sum(),
                "average_duration": df['duration_seconds'].mean(),
                "success_rate": (df['success'].sum() / len(df)) * 100,
                "date_range": {
                    "start": df['timestamp'].min().isoformat(),
                    "end": df['timestamp'].max().isoformat()
                }
            },
            "by_model": df.groupby('model').agg({
                'call_type': 'count',
                'duration_seconds': ['sum', 'mean'],
                'success': ['sum', 'mean']
            }).round(3).to_dict(),
            "by_agent": df.groupby('agent_context').agg({
                'call_type': 'count',
                'duration_seconds': ['sum', 'mean'],
                'success': ['sum', 'mean']
            }).round(3).to_dict(),
            "failed_calls": df[~df['success']]['error_message'].value_counts().to_dict(),
            "temperature_analysis": df.groupby('temperature')['duration_seconds'].agg(['count', 'mean']).round(3).to_dict()
        }
        
        return report

    def save_report(self, report: Dict, filename: str = None):
        """Save analysis report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"api_analysis_report_{timestamp}.json"
        
        report_path = self.logs_dir / filename
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report_path

    def create_visualizations(self, session_id: Optional[str] = None):
        """Create visualization charts for API usage."""
        df = self.load_api_calls(session_id=session_id)
        
        if df.empty:
            print("No data available for visualization")
            return
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # API calls by model
        model_counts = df['model'].value_counts()
        axes[0, 0].bar(model_counts.index, model_counts.values)
        axes[0, 0].set_title('API Calls by Model')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # Duration by agent
        agent_duration = df.groupby('agent_context')['duration_seconds'].sum()
        axes[0, 1].bar(agent_duration.index, agent_duration.values)
        axes[0, 1].set_title('Total Duration by Agent')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # Success rate over time
        df_hourly = df.set_index('timestamp').resample('H')['success'].mean()
        axes[1, 0].plot(df_hourly.index, df_hourly.values)
        axes[1, 0].set_title('Success Rate Over Time')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # Duration distribution
        axes[1, 1].hist(df['duration_seconds'], bins=20, alpha=0.7)
        axes[1, 1].set_title('API Call Duration Distribution')
        axes[1, 1].set_xlabel('Duration (seconds)')
        
        plt.tight_layout()
        
        # Save the plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_path = self.logs_dir / f"api_usage_charts_{timestamp}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        return plot_path

    def cleanup_old_logs(self, days_to_keep: int = 7):
        """Remove log files older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_str = cutoff_date.strftime("%Y%m%d")
        
        removed_files = []
        
        # Clean up API call logs
        for log_file in self.api_logs_dir.glob("api_calls_*.jsonl"):
            try:
                file_date_str = log_file.stem.split('_')[-1]
                if file_date_str < cutoff_str:
                    log_file.unlink()
                    removed_files.append(str(log_file))
            except (ValueError, IndexError):
                continue
        
        # Clean up other log types
        for log_dir in [self.agent_logs_dir, self.workflow_logs_dir]:
            for log_file in log_dir.glob("*.jsonl"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    removed_files.append(str(log_file))
        
        return removed_files

# Create global analyzer instance
log_analyzer = LogAnalyzer()