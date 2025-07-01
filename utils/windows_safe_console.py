"""
Windows-Safe Console Output Utility

This module provides utilities for safe console output on Windows systems
by replacing Unicode emojis with ASCII text equivalents.
"""

import sys
import logging
from typing import Any

# Emoji to text mapping for Windows compatibility
EMOJI_TO_TEXT = {
    # Progress indicators
    '🔄': '[PROCESSING]',
    '⏳': '[WAITING]',
    '🔃': '[REFRESH]',
    
    # Status indicators
    '✅': '[OK]',
    '❌': '[ERROR]',
    '⚠️': '[WARNING]',
    '📝': '[NOTE]',
    '📊': '[DATA]',
    '📈': '[STATS]',
    
    # Tools and actions
    '🔧': '[TOOL]',
    '🛠️': '[CONFIG]',
    '🔍': '[SEARCH]',
    '💾': '[SAVE]',
    '🎯': '[TARGET]',
    '⚡': '[FAST]',
    '🚀': '[LAUNCH]',
    '💡': '[IDEA]',
    '🎨': '[DESIGN]',
    '🔒': '[SECURE]',
    '🌐': '[WEB]',
    '🌟': '[SUCCESS]',
    '⭐': '[STAR]',
    
    # Package indicators
    '📦': '[PACKAGE]',
    '🔗': '[LINK]',
    '📁': '[FOLDER]',
    '📄': '[FILE]',
    
    # System status
    '🟢': '[ONLINE]',
    '🔴': '[OFFLINE]',
    '🟡': '[PENDING]',
    '🟠': '[WARNING]',
    
    # Agent-specific emojis (from SafeConsoleCallbackHandler)
    '🤖': '[AGENT]',
    '📥': '[INPUT]',
    '🏆': '[RESULT]',
    '🧠': '[LLM]',
    '💭': '[THINKING]',
    
    # General purpose
    '➡️': '[NEXT]',
    '⬅️': '[BACK]',
    '⬆️': '[UP]',
    '⬇️': '[DOWN]',
    '✨': '[NEW]',
    '🎉': '[DONE]',
    '👍': '[GOOD]',
    '👎': '[BAD]',
}

def safe_print(message: str, *args, **kwargs) -> None:
    """
    Safely print a message by replacing emojis with text equivalents.
    
    Args:
        message: The message to print
        *args: Additional arguments to pass to print()
        **kwargs: Additional keyword arguments to pass to print()
    """
    try:
        # Replace emojis with text equivalents
        safe_message = replace_emojis_with_text(message)
        print(safe_message, *args, **kwargs)
    except (ValueError, OSError, UnicodeEncodeError):
        # If print still fails, try with basic ASCII only
        try:
            ascii_message = safe_message.encode('ascii', errors='replace').decode('ascii')
            print(ascii_message, *args, **kwargs)
        except:
            # Last resort: log to file or ignore
            try:
                # Strip all emojis completely before logging
                ascii_only_message = strip_all_emojis(safe_message)
                logging.info(f"CONSOLE OUTPUT: {ascii_only_message}")
            except:
                pass  # Complete fallback - just ignore

def safe_input(prompt: str = "") -> str:
    """
    Safely get input with emoji-free prompt.
    
    Args:
        prompt: The input prompt
        
    Returns:
        User input string
    """
    safe_prompt = replace_emojis_with_text(prompt)
    try:
        return input(safe_prompt)
    except (ValueError, OSError, UnicodeEncodeError):
        # Fallback to basic ASCII
        ascii_prompt = safe_prompt.encode('ascii', errors='replace').decode('ascii')
        return input(ascii_prompt)

def replace_emojis_with_text(text: str) -> str:
    """
    Replace emojis in text with ASCII equivalents.
    
    Args:
        text: The text containing emojis
        
    Returns:
        Text with emojis replaced by ASCII equivalents
    """
    if not isinstance(text, str):
        text = str(text)
    
    result = text
    for emoji, replacement in EMOJI_TO_TEXT.items():
        result = result.replace(emoji, replacement)
    
    return result

def strip_all_emojis(text: str) -> str:
    """
    Remove all emoji characters from text, not just known ones.
    
    Args:
        text: The text containing emojis
        
    Returns:
        Text with all emojis removed
    """
    if not isinstance(text, str):
        text = str(text)
    
    # First replace known emojis with text
    result = replace_emojis_with_text(text)
    
    # Then remove any remaining Unicode emoji characters
    import re
    # Unicode ranges for emoji characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "]+", flags=re.UNICODE
    )
    result = emoji_pattern.sub('', result)
    
    return result

def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform.startswith('win')

def configure_safe_console():
    """
    Configure console for safe Unicode handling on Windows.
    This should be called at the start of the application.
    """
    if is_windows():
        # Try to enable UTF-8 mode if available
        try:
            import os
            os.environ['PYTHONIOENCODING'] = 'utf-8'
        except:
            pass

# Convenience functions for common patterns
def print_success(message: str) -> None:
    """Print a success message with safe formatting."""
    safe_print(f"✅ {message}")

def print_error(message: str) -> None:
    """Print an error message with safe formatting."""
    safe_print(f"❌ {message}")

def print_warning(message: str) -> None:
    """Print a warning message with safe formatting."""
    safe_print(f"⚠️ {message}")

def print_info(message: str) -> None:
    """Print an info message with safe formatting."""
    safe_print(f"📝 {message}")

def print_processing(message: str) -> None:
    """Print a processing message with safe formatting."""
    safe_print(f"🔄 {message}") 