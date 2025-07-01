"""
Windows Logging Fix for Unicode Characters
This module provides logging utilities that work properly on Windows systems
by handling Unicode encoding issues.
"""

import logging
import sys
import io
from typing import Any


class WindowsCompatibleStreamHandler(logging.StreamHandler):
    """
    A StreamHandler that properly handles Unicode on Windows systems.
    Prevents UnicodeEncodeError when logging emoji or other Unicode characters.
    """
    
    def __init__(self, stream=None):
        if stream is None:
            # Use stdout but wrap it with UTF-8 encoding
            if sys.platform.startswith('win'):
                stream = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                stream = sys.stdout
        super().__init__(stream)
    
    def emit(self, record):
        """Emit a record with proper error handling for Unicode."""
        try:
            msg = self.format(record)
            stream = self.stream
            
            # Handle Windows encoding issues
            if sys.platform.startswith('win'):
                # Replace problematic Unicode characters with safe alternatives
                msg = self._sanitize_for_windows(msg)
            
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)
    
    def _sanitize_for_windows(self, msg: str) -> str:
        """Replace Unicode characters that cause issues on Windows."""
        # Replace common emojis with text equivalents
        replacements = {
            '🧠': '[BRAIN]',
            '✅': '[OK]',
            '❌': '[ERROR]',
            '⚠️': '[WARNING]',
            '🧹': '[CLEAN]',
            '📊': '[STATS]',
            '📝': '[WRITE]',
            '📖': '[READ]',
            '❓': '[QUESTION]',
            '🌐': '[NETWORK]',
            '🔧': '[TOOL]',
            '⚡': '[FAST]',
            '🚀': '[ROCKET]',
            '💾': '[SAVE]',
            '🔍': '[SEARCH]',
            '📁': '[FOLDER]',
            '📄': '[FILE]',
            '🔄': '[REFRESH]',
            '🎯': '[TARGET]',
        }
        
        for emoji, replacement in replacements.items():
            msg = msg.replace(emoji, replacement)
        
        # Encode and decode to catch any remaining problematic characters
        try:
            msg.encode('cp1252')
        except UnicodeEncodeError:
            # If encoding fails, use ASCII with replacement
            msg = msg.encode('ascii', errors='replace').decode('ascii')
        
        return msg


def setup_windows_compatible_logging():
    """
    Setup logging that works properly on Windows systems.
    Call this early in your application to prevent Unicode errors.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Remove existing StreamHandlers that might cause issues
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, WindowsCompatibleStreamHandler):
            root_logger.removeHandler(handler)
    
    # Add our Windows-compatible handler if not already present
    has_compatible_handler = any(
        isinstance(h, WindowsCompatibleStreamHandler) 
        for h in root_logger.handlers
    )
    
    if not has_compatible_handler:
        handler = WindowsCompatibleStreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    return root_logger


def get_windows_safe_logger(name: str) -> logging.Logger:
    """
    Get a logger that's safe to use on Windows systems.
    
    Args:
        name: Logger name
        
    Returns:
        Logger configured for Windows compatibility
    """
    logger = logging.getLogger(name)
    
    # Ensure this logger uses Windows-compatible handlers
    if not any(isinstance(h, WindowsCompatibleStreamHandler) for h in logger.handlers):
        handler = WindowsCompatibleStreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False  # Don't propagate to root to avoid duplicates
    
    return logger


# Convenience function to replace emojis in strings
def sanitize_unicode_for_windows(text: str) -> str:
    """
    Replace Unicode characters that might cause issues on Windows.
    
    Args:
        text: Text that might contain problematic Unicode
        
    Returns:
        Sanitized text safe for Windows console
    """
    if not isinstance(text, str):
        text = str(text)
    
    replacements = {
        '🧠': '[BRAIN]',
        '✅': '[OK]',
        '❌': '[ERROR]',
        '⚠️': '[WARNING]',
        '🧹': '[CLEAN]',
        '📊': '[STATS]',
        '📝': '[WRITE]',
        '📖': '[READ]',
        '❓': '[QUESTION]',
        '🌐': '[NETWORK]',
        '🔧': '[TOOL]',
        '⚡': '[FAST]',
        '🚀': '[ROCKET]',
        '💾': '[SAVE]',
        '🔍': '[SEARCH]',
        '📁': '[FOLDER]',
        '📄': '[FILE]',
        '🔄': '[REFRESH]',
        '🎯': '[TARGET]',
    }
    
    for emoji, replacement in replacements.items():
        text = text.replace(emoji, replacement)
    
    return text 