"""Utility to export telegram messages to JSON."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from telethon.tl.types import Message, MessageMediaDocument, MessageMediaPhoto

logger = logging.getLogger("media_downloader")


def get_media_type_str(message: Message) -> Optional[str]:
    """
    Get media type as string from message.

    Parameters
    ----------
    message: Message
        The Telethon message object.

    Returns
    -------
    Optional[str]
        The media type ('photo', 'video', 'audio', 'voice', 'video_note', 'document')
        or None.
    """
    if not message.media:
        return None
    if isinstance(message.media, MessageMediaPhoto):
        return "photo"
    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        for attr in doc.attributes:
            if hasattr(attr, "voice") and isinstance(attr.voice, bool):
                return "voice" if attr.voice else "audio"
            if hasattr(attr, "round_message") and isinstance(attr.round_message, bool):
                return "video_note" if attr.round_message else "video"
        return "document"
    return None


def serialize_message(message: Message) -> Dict[str, Any]:
    """
    Convert a Message object to a JSON-serializable dictionary.

    Extracts:
    - Message ID, text content, sender info
    - Timestamps
    - Media type (if applicable)
    - Message reactions, forwards, replies

    Parameters
    ----------
    message: Message
        The Telethon message object to serialize.

    Returns
    -------
    Dict[str, Any]
        JSON-serializable dictionary representation of the message.
    """
    msg_dict = {
        "message_id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "text": message.text or "",
        "sender_id": message.sender_id,
        "chat_id": message.chat_id,
        "media_type": None,
        "media_file_name": None,
        "views": message.views or 0,
        "forwards": message.forwards or 0,
        "is_reply": message.is_reply,
        "reply_to_id": message.reply_to_msg_id if message.is_reply else None,
    }

    # Add media info if present
    if message.media:
        media_type = get_media_type_str(message)
        msg_dict["media_type"] = media_type
        if hasattr(message.media, "document"):
            doc = message.media.document
            if hasattr(doc, "attributes"):
                for attr in doc.attributes:
                    if hasattr(attr, "file_name"):
                        msg_dict["media_file_name"] = attr.file_name
                        break

    return msg_dict


def save_messages_to_json(
    messages: List[Message], file_path: str, append: bool = True
) -> None:
    """
    Save messages to JSON file.

    If append is True, new messages are merged with existing ones,
    avoiding duplicates based on message_id.

    Parameters
    ----------
    messages: List[Message]
        List of Telethon Message objects to serialize and save.
    file_path: str
        Path to save JSON file.
    append: bool
        If True, append to existing file; if False, overwrite.

    Returns
    -------
    None
    """
    serialized = [serialize_message(msg) for msg in messages]

    if append:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing = []

        # Merge, avoiding duplicates by message_id
        existing_ids = {msg["message_id"] for msg in existing}
        for msg in serialized:
            if msg["message_id"] not in existing_ids:
                existing.append(msg)
        serialized = existing

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2, ensure_ascii=False)

    logger.info("Exported %d messages to %s", len(serialized), file_path)
