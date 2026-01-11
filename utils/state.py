"""Download state management."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class DownloadState:
    """Manages download state for a session."""

    failed_ids: List[int] = field(default_factory=list)
    downloaded_ids: List[int] = field(default_factory=list)
    total_size_bytes: int = 0

    def mark_downloaded(self, message_id: int, file_size: int = 0) -> None:
        """
        Mark message as successfully downloaded.

        Parameters
        ----------
        message_id: int
            ID of the message that was downloaded.
        file_size: int
            Size of the downloaded file in bytes.
        """
        if message_id not in self.downloaded_ids:
            self.downloaded_ids.append(message_id)
            self.total_size_bytes += file_size

    def mark_failed(self, message_id: int) -> None:
        """
        Mark message as failed.

        Parameters
        ----------
        message_id: int
            ID of the message that failed.
        """
        if message_id not in self.failed_ids:
            self.failed_ids.append(message_id)

    def reset(self) -> None:
        """Reset state for new session."""
        self.failed_ids.clear()
        self.downloaded_ids.clear()
        self.total_size_bytes = 0

    def get_retry_ids(self, existing_retry_ids: List[int]) -> List[int]:
        """
        Calculate IDs to retry in next session.

        Parameters
        ----------
        existing_retry_ids: List[int]
            IDs already marked for retry in config.

        Returns
        -------
        List[int]
            Combined list of IDs to retry.
        """
        return (
            list(set(existing_retry_ids) - set(self.downloaded_ids))
            + self.failed_ids
        )
