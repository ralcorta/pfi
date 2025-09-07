"""Signal handling for graceful shutdown."""

import signal
import sys
from typing import Callable, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SignalHandler:
    """Handles system signals for graceful shutdown."""
    
    def __init__(self):
        """Initialize signal handler."""
        self.shutdown_callback: Optional[Callable[[], None]] = None
        self.is_shutting_down = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Signal handler initialized")
    
    def set_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """Set callback function to be called on shutdown.
        
        Args:
            callback: Function to call on shutdown
        """
        self.shutdown_callback = callback
        logger.debug("Shutdown callback set")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle system signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received signal {signal_name} ({signum})")
        
        if self.is_shutting_down:
            logger.warning("Already shutting down, forcing exit")
            sys.exit(1)
        
        self.is_shutting_down = True
        
        if self.shutdown_callback:
            try:
                logger.info("Calling shutdown callback")
                self.shutdown_callback()
            except Exception as e:
                logger.error("Error in shutdown callback", error=str(e))
        
        logger.info("Graceful shutdown completed")
        sys.exit(0)
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested.
        
        Returns:
            True if shutdown has been requested
        """
        return self.is_shutting_down
