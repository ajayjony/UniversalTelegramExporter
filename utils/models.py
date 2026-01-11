"""Data models for the application."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DownloadSummary:
    """Summary statistics for a download session."""

    total_messages: int
    """Total number of messages processed."""

    successful_downloads: int
    """Number of successfully downloaded files."""

    failed_downloads: int
    """Number of failed downloads."""

    skipped_messages: int
    """Number of messages skipped (no media or not matching filters)."""

    total_size_bytes: int
    """Total size of downloaded files in bytes."""

    duration_seconds: float
    """Total duration of download session in seconds."""

    def _format_size(self) -> str:
        """
        Format bytes to human-readable size.

        Returns
        -------
        str
            Human-readable file size (e.g., "1.5 GB")
        """
        size = self.total_size_bytes
        units = ["B", "KB", "MB", "GB", "TB"]

        for unit in units:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024

        return f"{size:.2f} PB"

    def get_success_rate(self) -> float:
        """
        Calculate download success rate as percentage.

        Returns
        -------
        float
            Success rate between 0 and 100, or 0 if no downloads attempted
        """
        total_attempts = self.successful_downloads + self.failed_downloads
        if total_attempts == 0:
            return 0.0

        return (self.successful_downloads / total_attempts) * 100

    def print_summary(self) -> None:
        """
        Print a formatted summary of the download session.

        Displays a formatted table with download statistics including
        total messages, success/failure counts, success rate, total
        size, and duration.

        Examples
        --------
        >>> summary = DownloadSummary(
        ...     total_messages=100,
        ...     successful_downloads=95,
        ...     failed_downloads=5,
        ...     skipped_messages=0,
        ...     total_size_bytes=1073741824,  # 1 GB
        ...     duration_seconds=120.5
        ... )
        >>> summary.print_summary()
        """
        success_rate = self.get_success_rate()
        size_str = self._format_size()

        summary_text = f"""
╔════════════════════════════════════════════════════════╗
║              DOWNLOAD SUMMARY                          ║
╠════════════════════════════════════════════════════════╣
║ Total Messages:        {self.total_messages:<30} ║
║ Successful Downloads:  {self.successful_downloads:<30} ║
║ Failed Downloads:      {self.failed_downloads:<30} ║
║ Skipped Messages:      {self.skipped_messages:<30} ║
║ Success Rate:          {success_rate:>28.1f}% ║
║ Total Size:            {size_str:>28} ║
║ Duration:              {self.duration_seconds:>27.1f}s ║
╚════════════════════════════════════════════════════════╝
"""
        print(summary_text)

    def __str__(self) -> str:
        """
        String representation of download summary.

        Returns
        -------
        str
            Formatted summary string
        """
        return (
            f"DownloadSummary(messages={self.total_messages}, "
            f"successful={self.successful_downloads}, "
            f"failed={self.failed_downloads}, "
            f"size={self._format_size()})"
        )
