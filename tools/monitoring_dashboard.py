"""
Real-time monitoring dashboard for the multi-AI development system.
Provides error tracking, performance monitoring, and system health insights.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

# Configure logging to capture system events
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('system_monitoring.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_monitoring_dashboard():
    """Create the main monitoring dashboard."""
    
    st.set_page_config(
        page_title="Multi-AI Dev System Monitor",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🔍 Multi-AI Development System Monitor")
    st.markdown("Real-time monitoring of code generation pipeline health and performance")
    
    # Sidebar controls
    st.sidebar.header("📊 Dashboard Controls")
    
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
    refresh_button = st.sidebar.button("🔄 Refresh Now")
    
    if auto_refresh:
        # Auto-refresh every 30 seconds
        placeholder = st.empty()
        time.sleep(30)
        st.rerun()
    
    # Main dashboard sections
    create_system_health_section()
    create_error_monitoring_section()
    create_performance_metrics_section()
    create_parsing_diagnostics_section()
    create_workflow_status_section()

def create_system_health_section():
    """Create system health overview section."""
    
    st.header("🏥 System Health Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📈 System Status",
            value="Healthy",
            delta="Normal operation"
        )
    
    with col2:
        st.metric(
            label="🔥 Active Workflows",
            value="3",
            delta="+1 from last hour"
        )
    
    with col3:
        st.metric(
            label="⚠️ Error Rate",
            value="2.3%",
            delta="-0.5% from yesterday"
        )
    
    with col4:
        st.metric(
            label="⚡ Avg Response Time",
            value="1.2s",
            delta="-0.3s improvement"
        )

def create_error_monitoring_section():
    """Create error monitoring and alerting section."""
    
    st.header("🚨 Error Monitoring & Alerts")
    
    # Load error data (this would come from the error handler in a real implementation)
    error_data = get_mock_error_data()
    
    if error_data:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Error timeline chart
            fig = px.bar(
                error_data,
                x='timestamp',
                y='count',
                color='severity',
                title="Error Timeline (Last 24 Hours)",
                color_discrete_map={
                    'LOW': '#28a745',
                    'MEDIUM': '#ffc107', 
                    'HIGH': '#fd7e14',
                    'CRITICAL': '#dc3545'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Error severity breakdown
            severity_counts = error_data.groupby('severity')['count'].sum().reset_index()
            fig_pie = px.pie(
                severity_counts,
                values='count',
                names='severity',
                title="Error Severity Distribution",
                color_discrete_map={
                    'LOW': '#28a745',
                    'MEDIUM': '#ffc107',
                    'HIGH': '#fd7e14', 
                    'CRITICAL': '#dc3545'
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Recent errors table
        st.subheader("🔍 Recent Errors")
        recent_errors = get_mock_recent_errors()
        
        df_errors = pd.DataFrame(recent_errors)
        
        # Apply color coding based on severity
        def highlight_severity(row):
            if row['Severity'] == 'CRITICAL':
                return ['background-color: #f8d7da'] * len(row)
            elif row['Severity'] == 'HIGH':
                return ['background-color: #fff3cd'] * len(row)
            else:
                return [''] * len(row)
        
        st.dataframe(
            df_errors.style.apply(highlight_severity, axis=1),
            use_container_width=True
        )
    
    else:
        st.success("✅ No errors detected in the last 24 hours!")

def create_performance_metrics_section():
    """Create performance monitoring section."""
    
    st.header("⚡ Performance Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Processing time trends
        time_data = get_mock_performance_data()
        fig = px.line(
            time_data,
            x='timestamp',
            y='processing_time',
            color='component',
            title="Processing Time Trends",
            labels={'processing_time': 'Time (seconds)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Success rate over time
        success_data = get_mock_success_rate_data()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=success_data['timestamp'],
            y=success_data['success_rate'],
            mode='lines+markers',
            name='Success Rate',
            line=dict(color='#28a745', width=3)
        ))
        fig.update_layout(
            title="Success Rate Over Time",
            yaxis_title="Success Rate (%)",
            yaxis=dict(range=[0, 100])
        )
        st.plotly_chart(fig, use_container_width=True)

def create_parsing_diagnostics_section():
    """Create LLM output parsing diagnostics section."""
    
    st.header("🔍 LLM Output Parsing Diagnostics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="📄 Files Parsed Successfully",
            value="1,247",
            delta="+23 from last hour"
        )
    
    with col2:
        st.metric(
            label="❌ Parsing Failures",
            value="8",
            delta="-12 from yesterday"
        )
    
    with col3:
        st.metric(
            label="🔧 Recovery Success Rate",
            value="87.5%",
            delta="+5.2% improvement"
        )
    
    # Parsing pattern analysis
    st.subheader("📊 Parsing Pattern Analysis")
    
    parsing_data = get_mock_parsing_data()
    fig = px.bar(
        parsing_data,
        x='pattern_type',
        y='success_count',
        color='parser_strategy',
        title="Parsing Success by Pattern Type and Strategy",
        labels={'success_count': 'Successful Parses'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Common parsing issues
    st.subheader("⚠️ Common Parsing Issues")
    
    issues_data = [
        {"Issue": "Unmatched code blocks", "Frequency": 45, "Impact": "Medium"},
        {"Issue": "Missing file extensions", "Frequency": 23, "Impact": "Low"},
        {"Issue": "Invalid file paths", "Frequency": 12, "Impact": "High"},
        {"Issue": "Empty content blocks", "Frequency": 8, "Impact": "Critical"}
    ]
    
    df_issues = pd.DataFrame(issues_data)
    st.dataframe(df_issues, use_container_width=True)

def create_workflow_status_section():
    """Create workflow status tracking section."""
    
    st.header("🔄 Workflow Status Tracking")
    
    # Active workflows
    st.subheader("📋 Active Workflows")
    
    workflows = get_mock_workflow_data()
    df_workflows = pd.DataFrame(workflows)
    
    # Progress bars for each workflow
    for _, workflow in df_workflows.iterrows():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{workflow['name']}** (ID: {workflow['id']})")
            progress = workflow['progress'] / 100
            st.progress(progress, text=f"{workflow['progress']}% complete")
        
        with col2:
            status_color = {
                'Running': '🟢',
                'Paused': '🟡',
                'Error': '🔴',
                'Completed': '✅'
            }
            st.write(f"Status: {status_color.get(workflow['status'], '⚪')} {workflow['status']}")
        
        with col3:
            st.write(f"ETA: {workflow['eta']}")

# Mock data functions (in a real implementation, these would connect to actual data sources)

def get_mock_error_data():
    """Generate mock error data for demonstration."""
    timestamps = pd.date_range(start=datetime.now() - timedelta(hours=24), end=datetime.now(), freq='H')
    
    data = []
    for ts in timestamps:
        for severity in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            count = max(0, int(pd.np.random.normal(2, 1))) if severity != 'CRITICAL' else max(0, int(pd.np.random.normal(0.5, 0.3)))
            if count > 0:
                data.append({
                    'timestamp': ts,
                    'severity': severity,
                    'count': count
                })
    
    return pd.DataFrame(data)

def get_mock_recent_errors():
    """Generate mock recent errors for demonstration."""
    return [
        {
            'Timestamp': '2025-07-13 12:32:15',
            'Module': 'LLM_Parsing',
            'Error Type': 'PatternMatchError',
            'Severity': 'HIGH',
            'Message': 'Failed to parse LLM output with ### filename.ext pattern',
            'Work Item': 'FB-001'
        },
        {
            'Timestamp': '2025-07-13 12:28:42',
            'Module': 'Code_Generation',
            'Error Type': 'ValidationError',
            'Severity': 'MEDIUM',
            'Message': 'Generated file missing required content',
            'Work Item': 'FB-002'
        },
        {
            'Timestamp': '2025-07-13 12:15:33',
            'Module': 'File_Validation',
            'Error Type': 'ContentError',
            'Severity': 'LOW',
            'Message': 'Content too short: 8 characters',
            'Work Item': 'FB-003'
        }
    ]

def get_mock_performance_data():
    """Generate mock performance data."""
    timestamps = pd.date_range(start=datetime.now() - timedelta(hours=6), end=datetime.now(), freq='15min')
    
    data = []
    for ts in timestamps:
        for component in ['BRD Analysis', 'Code Generation', 'Tech Stack', 'System Design']:
            base_time = {'BRD Analysis': 3.2, 'Code Generation': 8.5, 'Tech Stack': 2.1, 'System Design': 4.7}
            processing_time = base_time[component] + pd.np.random.normal(0, 0.5)
            data.append({
                'timestamp': ts,
                'component': component,
                'processing_time': max(0.1, processing_time)
            })
    
    return pd.DataFrame(data)

def get_mock_success_rate_data():
    """Generate mock success rate data."""
    timestamps = pd.date_range(start=datetime.now() - timedelta(hours=12), end=datetime.now(), freq='30min')
    
    success_rates = []
    base_rate = 92.5
    
    for ts in timestamps:
        rate = base_rate + pd.np.random.normal(0, 3)
        rate = max(85, min(100, rate))  # Keep between 85-100%
        success_rates.append({'timestamp': ts, 'success_rate': rate})
    
    return pd.DataFrame(success_rates)

def get_mock_parsing_data():
    """Generate mock parsing data."""
    return pd.DataFrame([
        {'pattern_type': '### FILE: path', 'parser_strategy': 'Standard', 'success_count': 342},
        {'pattern_type': '### filename.ext', 'parser_strategy': 'Enhanced', 'success_count': 567},
        {'pattern_type': '**filename**', 'parser_strategy': 'Bold', 'success_count': 123},
        {'pattern_type': 'Code blocks', 'parser_strategy': 'Aggressive', 'success_count': 234},
        {'pattern_type': 'Emergency', 'parser_strategy': 'Fallback', 'success_count': 45}
    ])

def get_mock_workflow_data():
    """Generate mock workflow data."""
    return [
        {
            'id': 'WF-001',
            'name': 'E-commerce Platform Development',
            'progress': 67,
            'status': 'Running',
            'eta': '2h 15m'
        },
        {
            'id': 'WF-002', 
            'name': 'API Gateway Implementation',
            'progress': 23,
            'status': 'Running',
            'eta': '4h 30m'
        },
        {
            'id': 'WF-003',
            'name': 'Database Migration Tool',
            'progress': 89,
            'status': 'Running',
            'eta': '45m'
        }
    ]

if __name__ == "__main__":
    create_monitoring_dashboard()
