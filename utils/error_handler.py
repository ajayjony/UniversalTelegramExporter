"""User-friendly error messages and handling."""

from enum import Enum
from typing import Dict, Optional


class UserFriendlyError(Enum):
    """User-friendly error messages with solutions."""

    FILE_REFERENCE_EXPIRED = {
        "title": "❌ File Reference Expired",
        "description": "Telegram removed access to this file (it was too old or deleted)",
        "solution": "The file will be automatically retried on your next run",
        "severity": "WARNING",
    }

    TIMEOUT = {
        "title": "❌ Download Timeout",
        "description": "The download took too long and was cancelled",
        "solution": "Check your internet connection. The file will be retried.",
        "severity": "WARNING",
    }

    BAD_REQUEST = {
        "title": "❌ Bad Request",
        "description": "Invalid request sent to Telegram servers",
        "solution": "This usually happens with corrupted files. The file will be skipped.",
        "severity": "ERROR",
    }

    UNAUTHORIZED = {
        "title": "❌ Unauthorized",
        "description": "Your Telegram session is no longer valid",
        "solution": "Delete session file and re-authenticate",
        "severity": "ERROR",
    }

    FILE_TOO_LARGE = {
        "title": "❌ File Too Large",
        "description": "This file is larger than 2GB (Telegram limit)",
        "solution": "Unfortunately this file cannot be downloaded",
        "severity": "ERROR",
    }

    NETWORK_ERROR = {
        "title": "❌ Network Error",
        "description": "Connection to Telegram failed",
        "solution": "Check your internet connection and try again",
        "severity": "WARNING",
    }

    DIRECTORY_NOT_FOUND = {
        "title": "❌ Directory Not Found",
        "description": "Output directory doesn't exist and cannot be created",
        "solution": "Check directory path permissions and try again",
        "severity": "ERROR",
    }

    CONFIG_INVALID = {
        "title": "❌ Invalid Configuration",
        "description": "Configuration file has invalid values",
        "solution": "Check your config.yaml file for errors",
        "severity": "ERROR",
    }

    UNKNOWN_ERROR = {
        "title": "❌ Unknown Error",
        "description": "An unexpected error occurred",
        "solution": "Check the logs for details or report the issue",
        "severity": "ERROR",
    }

    def format_message(self) -> str:
        """
        Format error message for user display.

        Returns
        -------
        str
            Formatted error message
        """
        info = self.value
        return (
            f"\n{info['title']}\n"
            f"   📝 {info['description']}\n"
            f"   💡 Solution: {info['solution']}\n"
        )

    def get_severity(self) -> str:
        """Get error severity level."""
        return self.value.get("severity", "WARNING")

    @classmethod
    def from_exception(cls, exception: Exception) -> "UserFriendlyError":
        """
        Map exception type to user-friendly error.

        Parameters
        ----------
        exception : Exception
            Python exception instance

        Returns
        -------
        UserFriendlyError
            Corresponding user-friendly error
        """
        exception_type = type(exception).__name__

        mapping = {
            "FileReferenceExpiredError": cls.FILE_REFERENCE_EXPIRED,
            "TimeoutError": cls.TIMEOUT,
            "BadRequestError": cls.BAD_REQUEST,
            "AuthorizationError": cls.UNAUTHORIZED,
            "FloodWaitError": cls.TIMEOUT,
            "ConnectionError": cls.NETWORK_ERROR,
            "OSError": cls.DIRECTORY_NOT_FOUND,
            "ValueError": cls.CONFIG_INVALID,
        }

        return mapping.get(exception_type, cls.UNKNOWN_ERROR)


class ErrorHandler:
    """Handle errors with user-friendly messages."""

    def __init__(self):
        """Initialize error handler."""
        self.error_count = 0
        self.warnings_count = 0

    def handle_error(
        self,
        exception: Exception,
        message_id: Optional[int] = None,
        logger=None,
        critical: bool = False,
    ) -> None:
        """
        Handle an error and log user-friendly message.

        Parameters
        ----------
        exception : Exception
            The exception that occurred
        message_id : Optional[int]
            Telegram message ID if applicable
        logger : logging.Logger
            Logger instance for output
        critical : bool
            Whether this is a critical error
        """
        user_error = UserFriendlyError.from_exception(exception)

        if logger:
            message_prefix = f"Message[{message_id}]: " if message_id else ""
            
            if critical or user_error.get_severity() == "ERROR":
                logger.error(f"{message_prefix}{user_error.format_message()}")
                self.error_count += 1
            else:
                logger.warning(f"{message_prefix}{user_error.format_message()}")
                self.warnings_count += 1

            # Also log the original exception at DEBUG level
            logger.debug(f"Original exception: {type(exception).__name__}: {str(exception)}", 
                        exc_info=True)

    def get_summary(self) -> str:
        """
        Get error summary for reporting.

        Returns
        -------
        str
            Summary of errors and warnings
        """
        if self.error_count == 0 and self.warnings_count == 0:
            return "✅ No errors or warnings"

        parts = []
        if self.error_count > 0:
            parts.append(f"❌ {self.error_count} error{'s' if self.error_count != 1 else ''}")
        if self.warnings_count > 0:
            parts.append(f"⚠️ {self.warnings_count} warning{'s' if self.warnings_count != 1 else ''}")

        return ", ".join(parts)

    def reset(self) -> None:
        """Reset error counters."""
        self.error_count = 0
        self.warnings_count = 0
