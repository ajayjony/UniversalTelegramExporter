"""Custom exceptions for download operations."""

from enum import Enum


class DownloadErrorType(Enum):
    """Types of download errors."""

    FILE_REFERENCE_EXPIRED = "file_reference_expired"
    TIMEOUT = "timeout"
    UNAUTHORIZED = "unauthorized"
    FILE_TOO_LARGE = "file_too_large"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class DownloadError(Exception):
    """
    Custom exception for download errors.

    Provides more context about the error type and whether it's retryable.
    """

    def __init__(
        self,
        message: str,
        error_type: DownloadErrorType = DownloadErrorType.UNKNOWN,
        retry_count: int = 0,
        is_retryable: bool = False,
    ):
        """
        Initialize DownloadError.

        Parameters
        ----------
        message: str
            Human-readable error message.
        error_type: DownloadErrorType
            Type of error that occurred.
        retry_count: int
            Number of times this has been retried.
        is_retryable: bool
            Whether this error should trigger a retry.
        """
        self.message = message
        self.error_type = error_type
        self.retry_count = retry_count
        self.is_retryable = is_retryable
        super().__init__(self.message)
