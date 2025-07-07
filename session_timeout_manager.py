"""
Session Timeout Extension Manager
Handles extended timeouts for human approval periods
"""

import time
import threading
import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class SessionInfo:
    """Information about an active session"""
    session_id: str
    last_activity: float
    timeout_seconds: int
    is_human_approval: bool
    approval_type: str
    created_at: float
    extended_count: int = 0

class SessionTimeoutManager:
    """
    Manages session timeouts with special handling for human approval periods
    
    Features:
    - Extended timeouts during human approval
    - Automatic session cleanup
    - Session activity tracking
    - Timeout warnings and notifications
    """
    
    def __init__(self, 
                 default_timeout: int = 3600,      # 1 hour default
                 approval_timeout: int = 7200,     # 2 hours for approvals
                 max_approval_timeout: int = 86400, # 24 hours max
                 cleanup_interval: int = 300):     # 5 minutes cleanup
        
        self.default_timeout = default_timeout
        self.approval_timeout = approval_timeout
        self.max_approval_timeout = max_approval_timeout
        self.cleanup_interval = cleanup_interval
        
        # Session tracking
        self.sessions: Dict[str, SessionInfo] = {}
        self._lock = threading.RLock()
        
        # Cleanup thread
        self._cleanup_thread = None
        self._should_stop = threading.Event()
        
        # Callbacks
        self.timeout_warning_callback: Optional[Callable] = None
        self.session_expired_callback: Optional[Callable] = None
        
        # Start cleanup thread
        self.start_cleanup_thread()
        
        logger.info("Session Timeout Manager initialized")
    
    def create_session(self, session_id: str, is_human_approval: bool = False, 
                      approval_type: str = None) -> SessionInfo:
        """
        Create or update a session with appropriate timeout
        
        Args:
            session_id: Unique session identifier
            is_human_approval: Whether this is a human approval session
            approval_type: Type of approval (brd, tech_stack, system_design, plan)
            
        Returns:
            SessionInfo object for the created/updated session
        """
        with self._lock:
            current_time = time.time()
            
            # Determine timeout based on session type
            if is_human_approval:
                timeout = self.approval_timeout
            else:
                timeout = self.default_timeout
            
            session_info = SessionInfo(
                session_id=session_id,
                last_activity=current_time,
                timeout_seconds=timeout,
                is_human_approval=is_human_approval,
                approval_type=approval_type or "none",
                created_at=current_time
            )
            
            self.sessions[session_id] = session_info
            
            logger.info(f"Session created: {session_id} (timeout: {timeout}s, approval: {is_human_approval})")
            return session_info
    
    def update_activity(self, session_id: str):
        """Update the last activity time for a session"""
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id].last_activity = time.time()
                logger.debug(f"Activity updated for session: {session_id}")
            else:
                logger.warning(f"Attempted to update activity for unknown session: {session_id}")
    
    def extend_session_timeout(self, session_id: str, additional_seconds: int = None) -> bool:
        """
        Extend the timeout for a session
        
        Args:
            session_id: Session to extend
            additional_seconds: Additional time to add (defaults to approval_timeout)
            
        Returns:
            True if extension was successful
        """
        with self._lock:
            if session_id not in self.sessions:
                logger.warning(f"Cannot extend unknown session: {session_id}")
                return False
            
            session = self.sessions[session_id]
            
            # Calculate extension
            if additional_seconds is None:
                additional_seconds = self.approval_timeout
            
            new_timeout = session.timeout_seconds + additional_seconds
            
            # Check maximum timeout limit
            if new_timeout > self.max_approval_timeout:
                new_timeout = self.max_approval_timeout
                logger.warning(f"Session timeout capped at maximum: {session_id}")
            
            session.timeout_seconds = new_timeout
            session.extended_count += 1
            session.last_activity = time.time()  # Reset activity timer
            
            logger.info(f"Session timeout extended: {session_id} (+{additional_seconds}s, total: {new_timeout}s)")
            return True
    
    def start_human_approval(self, session_id: str, approval_type: str) -> SessionInfo:
        """
        Transition a session to human approval mode with extended timeout
        
        Args:
            session_id: Session identifier
            approval_type: Type of approval (brd, tech_stack, system_design, plan)
            
        Returns:
            Updated SessionInfo
        """
        with self._lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.is_human_approval = True
                session.approval_type = approval_type
                session.timeout_seconds = self.approval_timeout
                session.last_activity = time.time()
                
                logger.info(f"Session transitioned to human approval: {session_id} ({approval_type})")
                return session
            else:
                # Create new approval session
                return self.create_session(session_id, True, approval_type)
    
    def end_human_approval(self, session_id: str) -> bool:
        """
        End human approval mode and return to normal timeout
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful
        """
        with self._lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.is_human_approval = False
                session.approval_type = "none"
                session.timeout_seconds = self.default_timeout
                session.last_activity = time.time()
                
                logger.info(f"Session returned to normal timeout: {session_id}")
                return True
            
            logger.warning(f"Cannot end approval for unknown session: {session_id}")
            return False
    
    def is_session_active(self, session_id: str) -> bool:
        """Check if a session is still active (not timed out)"""
        with self._lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            current_time = time.time()
            elapsed = current_time - session.last_activity
            
            return elapsed < session.timeout_seconds
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Get information about a session"""
        with self._lock:
            return self.sessions.get(session_id)
    
    def get_time_remaining(self, session_id: str) -> Optional[int]:
        """Get the time remaining before session timeout"""
        with self._lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            current_time = time.time()
            elapsed = current_time - session.last_activity
            remaining = session.timeout_seconds - elapsed
            
            return max(0, int(remaining))
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        with self._lock:
            current_time = time.time()
            expired_sessions = []
            
            for session_id, session in self.sessions.items():
                elapsed = current_time - session.last_activity
                if elapsed >= session.timeout_seconds:
                    expired_sessions.append(session_id)
            
            # Remove expired sessions
            for session_id in expired_sessions:
                session_info = self.sessions.pop(session_id)
                logger.info(f"Session expired and removed: {session_id}")
                
                # Notify callback if configured
                if self.session_expired_callback:
                    try:
                        self.session_expired_callback(session_id, session_info)
                    except Exception as e:
                        logger.error(f"Error in session expired callback: {e}")
            
            return len(expired_sessions)
    
    def check_timeout_warnings(self):
        """Check for sessions approaching timeout and send warnings"""
        with self._lock:
            current_time = time.time()
            warning_threshold = 300  # 5 minutes warning
            
            for session_id, session in self.sessions.items():
                elapsed = current_time - session.last_activity
                remaining = session.timeout_seconds - elapsed
                
                # Send warning if approaching timeout
                if 0 < remaining <= warning_threshold:
                    logger.warning(f"Session approaching timeout: {session_id} ({remaining}s remaining)")
                    
                    # Notify callback if configured
                    if self.timeout_warning_callback:
                        try:
                            self.timeout_warning_callback(session_id, int(remaining))
                        except Exception as e:
                            logger.error(f"Error in timeout warning callback: {e}")
    
    def start_cleanup_thread(self):
        """Start the background cleanup thread"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return
        
        self._should_stop.clear()
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        
        logger.info("Session cleanup thread started")
    
    def stop_cleanup_thread(self):
        """Stop the background cleanup thread"""
        self._should_stop.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        
        logger.info("Session cleanup thread stopped")
    
    def _cleanup_worker(self):
        """Worker function for session cleanup"""
        while not self._should_stop.wait(self.cleanup_interval):
            try:
                # Cleanup expired sessions
                expired_count = self.cleanup_expired_sessions()
                
                # Check for timeout warnings
                self.check_timeout_warnings()
                
                if expired_count > 0:
                    logger.debug(f"Cleaned up {expired_count} expired sessions")
                    
            except Exception as e:
                logger.error(f"Error in session cleanup worker: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about session management"""
        with self._lock:
            current_time = time.time()
            
            stats = {
                "total_sessions": len(self.sessions),
                "approval_sessions": sum(1 for s in self.sessions.values() if s.is_human_approval),
                "normal_sessions": sum(1 for s in self.sessions.values() if not s.is_human_approval),
                "extended_sessions": sum(1 for s in self.sessions.values() if s.extended_count > 0),
                "average_session_age": 0,
                "approval_types": {}
            }
            
            if self.sessions:
                total_age = sum(current_time - s.created_at for s in self.sessions.values())
                stats["average_session_age"] = total_age / len(self.sessions)
                
                # Count approval types
                for session in self.sessions.values():
                    if session.is_human_approval:
                        approval_type = session.approval_type
                        stats["approval_types"][approval_type] = stats["approval_types"].get(approval_type, 0) + 1
            
            return stats