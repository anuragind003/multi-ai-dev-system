"""
Message Bus for decoupled agent communication.
Provides publish-subscribe pattern for agent interaction.
"""

import logging
import threading
import time
import uuid
import json
from typing import Dict, Any, Callable, List, Optional
from queue import Queue, Empty


_message_bus_instance: Optional["MessageBus"] = None


class MessageBus:
    """Inter-agent communication system using a pub/sub model."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize message bus with required attributes."""
        self.subscribers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger("MessageBus")
        self.message_history: List[Dict[str, Any]] = []
        self.lock = threading.RLock()  # RLock for reentrant lock
        
        self.max_history = max_history
        self.message_queue = Queue()
        
        # Thread for processing messages
        self._running = True
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()
        self.logger.info("MessageBus initialized and processing thread started.")
        
    def publish(self, message_type: str, payload: Dict[str, Any]) -> str:
        """
        Publish a message to all subscribers of a specific message type.
        
        Args:
            message_type: The type of message (e.g., "brd.analysis.complete")
            payload: The message data
            
        Returns:
            message_id: Unique ID for the published message
        """
        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "type": message_type,
            "payload": payload,
            "timestamp": time.time()
        }
        
        self.logger.debug(f"Publishing message: {message_type} (ID: {message_id})")
        
        # Add to message history with thread safety
        with self.lock:
            self.message_history.append(message)
            if len(self.message_history) > self.max_history:
                self.message_history = self.message_history[-self.max_history:]
        
        # Add to processing queue instead of direct delivery
        self.message_queue.put(message)
        return message_id
    
    def _process_queue(self):
        """Background thread to process the message queue"""
        self.logger.info("MessageBus._process_queue thread started.")
        while self._running:
            try:
                message = self.message_queue.get(timeout=1.0)
                self._deliver_message(message)
                self.message_queue.task_done()
            except Empty:
                # This is normal for timeout when queue is empty
                continue
            except Exception as e:
                # Log any other unexpected exceptions
                self.logger.error(f"Error processing message from queue: {e}", exc_info=True)
        self.logger.info("MessageBus._process_queue thread stopped.")
    
    def _deliver_message(self, message: Dict[str, Any]):
        """Deliver a message to all relevant subscribers"""
        message_type = message["type"]
        subscribers_notified_count = 0
        
        # Deliver to exact type subscribers
        # Use a copy of subscribers list in case callbacks modify the list
        exact_subscribers = []
        with self.lock:
            if message_type in self.subscribers:
                exact_subscribers = list(self.subscribers[message_type])
        
        if exact_subscribers:
            self.logger.debug(f"Delivering to {len(exact_subscribers)} exact subscribers for {message_type}")
            self._notify_subscribers(message, exact_subscribers)
            subscribers_notified_count += len(exact_subscribers)
        
        # Deliver to wildcard subscribers (e.g., "brd.*" would match "brd.analysis.complete")
        wildcard_subscriber_patterns_notified = set()
        
        # Iterate over a copy of subscriber items for thread safety
        current_subscriber_items = []
        with self.lock:
            current_subscriber_items = list(self.subscribers.items())
        
        for pattern, pattern_subscribers_list in current_subscriber_items:
            if '*' in pattern:
                # Simple wildcard matching (ends with *)
                if pattern.endswith('*'):
                    base_pattern = pattern[:-1]
                    if message_type.startswith(base_pattern):
                        if pattern not in wildcard_subscriber_patterns_notified:
                            subscribers_to_notify_for_pattern = list(pattern_subscribers_list)
                            self.logger.debug(f"Delivering to {len(subscribers_to_notify_for_pattern)} subscribers for wildcard pattern {pattern} matching {message_type}")
                            self._notify_subscribers(message, subscribers_to_notify_for_pattern)
                            subscribers_notified_count += len(subscribers_to_notify_for_pattern)
                            wildcard_subscriber_patterns_notified.add(pattern)
        
        if subscribers_notified_count == 0:
            self.logger.debug(f"No subscribers found for message type: {message_type} (ID: {message['id']})")
    
    def _notify_subscribers(self, message: Dict[str, Any], subscribers: List[Callable]):
        """Notify a list of subscribers about a message"""
        for callback in subscribers:
            try:
                callback(message)
            except Exception as e:
                self.logger.error(f"Error in subscriber callback for message {message['id']} (type: {message['type']}): {e}", exc_info=True)
    
    def subscribe(self, message_type: str, callback: Callable) -> None:
        """
        Subscribe to a specific message type or pattern.
        
        Args:
            message_type: Type of messages to subscribe to (can include wildcards, e.g., "brd.*")
            callback: Function that will be called when a matching message is published
        """
        with self.lock:
            if message_type not in self.subscribers:
                self.subscribers[message_type] = []
            
            if callback not in self.subscribers[message_type]:
                self.subscribers[message_type].append(callback)
                self.logger.debug(f"New subscriber {callback.__name__ if hasattr(callback, '__name__') else callback} added for: {message_type}")
            else:
                self.logger.debug(f"Subscriber {callback.__name__ if hasattr(callback, '__name__') else callback} already subscribed to: {message_type}")
    
    def unsubscribe(self, message_type: str, callback: Callable) -> bool:
        """
        Unsubscribe from a specific message type.
        
        Args:
            message_type: Type of messages to unsubscribe from
            callback: Function to remove from subscribers
            
        Returns:
            bool: True if successfully unsubscribed, False otherwise
        """
        with self.lock:
            if message_type in self.subscribers and callback in self.subscribers[message_type]:
                self.subscribers[message_type].remove(callback)
                self.logger.debug(f"Subscriber {callback.__name__ if hasattr(callback, '__name__') else callback} removed from: {message_type}")
                if not self.subscribers[message_type]:
                    del self.subscribers[message_type]
                    self.logger.debug(f"Removed message type {message_type} from subscribers (no listeners).")
                return True
        self.logger.warning(f"Failed to unsubscribe: Subscriber or message type {message_type} not found.")
        return False
    
    def get_message_history(self, limit: int = 100, message_type: str = None) -> List[Dict[str, Any]]:
        """
        Get recent messages from history, optionally filtered by type.
        
        Args:
            limit: Maximum number of messages to return
            message_type: Optional filter by message type
            
        Returns:
            List of messages
        """
        with self.lock:
            history_copy = list(self.message_history)
            if message_type:
                filtered = [m for m in history_copy if m["type"] == message_type]
                return filtered[-limit:]
            else:
                return history_copy[-limit:]
                
    def __del__(self):
        """Clean up resources when the object is garbage collected"""
        self.logger.info("MessageBus shutting down...")
        self._running = False
        if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
            self.logger.debug("Joining processing thread...")
            self.processing_thread.join(timeout=2.0)
            if self.processing_thread.is_alive():
                self.logger.warning("Processing thread did not terminate in time.")
        self.logger.info("MessageBus shutdown complete.")
    
    # The following methods should be moved to their respective agent classes
    def subscribe_to_messages(self) -> None:
        """Subscribe to relevant messages from other agents"""
        self.logger.warning("METHOD 'subscribe_to_messages' IS MISPLACED IN MessageBus. Move to agent class.")
        if hasattr(self, 'message_bus'):
            pass
            
    def _handle_code_generation(self, message: Dict[str, Any]) -> None:
        """Handle code generation completion messages"""
        self.logger.warning("METHOD '_handle_code_generation' IS MISPLACED IN MessageBus. Move to agent class.")
        pass
    
    def log_message(self, level, message):
        """Log message with appropriate level."""
        self.logger.warning("METHOD 'log_message' IS MISPLACED/REDUNDANT IN MessageBus.")
        if level.lower() == 'debug':
            self.logger.debug(message)
        elif level.lower() == 'info':
            self.logger.info(message)
        elif level.lower() == 'warning':
            self.logger.warning(message)
        elif level.lower() == 'error':
            self.logger.error(message)
        else:
            self.logger.info(message)


def get_message_bus() -> "MessageBus":
    """
    Singleton accessor for the MessageBus.
    This ensures a single instance is used throughout the application.
    """
    global _message_bus_instance
    if _message_bus_instance is None:
        logging.getLogger("MessageBus").info("Creating a new global instance of MessageBus.")
        _message_bus_instance = MessageBus()
    return _message_bus_instance