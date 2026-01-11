"""Unit tests for message export utility."""

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

from telethon.tl.types import Message, MessageMediaDocument, MessageMediaPhoto

from utils.message_export import get_media_type_str, save_messages_to_json, serialize_message


class MockMessage:
    """Mock Telethon Message for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.date = kwargs.get("date", datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc))
        self.text = kwargs.get("text", "Test message")
        self.sender_id = kwargs.get("sender_id", 123456789)
        self.chat_id = kwargs.get("chat_id", -1001234567890)
        self.media = kwargs.get("media", None)
        self.views = kwargs.get("views", 0)
        self.forwards = kwargs.get("forwards", 0)
        self.is_reply = kwargs.get("is_reply", False)
        self.reply_to_msg_id = kwargs.get("reply_to_msg_id", None)


class MockMediaObject:
    """Mock media object."""

    def __init__(self, **kwargs):
        self.mime_type = kwargs.get("mime_type", "application/octet-stream")
        self.attributes = kwargs.get("attributes", [])


class MockVoiceAttribute:
    """Mock voice attribute."""

    def __init__(self):
        self.voice = True


class MockVideoAttribute:
    """Mock video attribute."""

    def __init__(self):
        self.voice = False


class MessageExportTestCase(unittest.TestCase):
    """Test cases for message export functionality."""

    def test_serialize_message_simple(self):
        """Test serializing a simple text message."""
        message = MockMessage(
            id=100,
            text="Hello world",
            sender_id=987654321,
            chat_id=-1001174318146,
        )
        result = serialize_message(message)

        self.assertEqual(result["message_id"], 100)
        self.assertEqual(result["text"], "Hello world")
        self.assertEqual(result["sender_id"], 987654321)
        self.assertEqual(result["chat_id"], -1001174318146)
        self.assertIsNone(result["media_type"])
        self.assertEqual(result["views"], 0)
        self.assertEqual(result["forwards"], 0)

    def test_serialize_message_with_media(self):
        """Test serializing a message with media."""
        media = mock.Mock(spec=MessageMediaPhoto)
        message = MockMessage(
            id=101,
            text="Photo message",
            media=media,
        )
        result = serialize_message(message)

        self.assertEqual(result["message_id"], 101)
        self.assertEqual(result["text"], "Photo message")
        self.assertEqual(result["media_type"], "photo")

    def test_serialize_message_with_reply(self):
        """Test serializing a reply message."""
        message = MockMessage(
            id=102,
            text="This is a reply",
            is_reply=True,
            reply_to_msg_id=100,
        )
        result = serialize_message(message)

        self.assertEqual(result["message_id"], 102)
        self.assertTrue(result["is_reply"])
        self.assertEqual(result["reply_to_id"], 100)

    def test_serialize_message_timestamp_format(self):
        """Test that timestamps are properly ISO formatted."""
        test_date = datetime(2024, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        message = MockMessage(id=103, date=test_date)
        result = serialize_message(message)

        self.assertEqual(result["date"], "2024-01-15T14:30:45+00:00")

    def test_get_media_type_str_photo(self):
        """Test media type detection for photos."""
        media = mock.Mock(spec=MessageMediaPhoto)
        message = MockMessage(media=media)

        result = get_media_type_str(message)
        self.assertEqual(result, "photo")

    def test_get_media_type_str_voice(self):
        """Test media type detection for voice messages."""
        voice_attr = MockVoiceAttribute()
        doc_media = mock.Mock(spec=MessageMediaDocument)
        doc_media.document = mock.Mock()
        doc_media.document.attributes = [voice_attr]

        message = MockMessage(media=doc_media)
        result = get_media_type_str(message)
        self.assertEqual(result, "voice")

    def test_get_media_type_str_none(self):
        """Test media type detection for messages without media."""
        message = MockMessage(media=None)
        result = get_media_type_str(message)
        self.assertIsNone(result)

    def test_save_messages_to_json_new_file(self):
        """Test saving messages to a new JSON file."""
        messages = [
            MockMessage(id=1, text="Message 1"),
            MockMessage(id=2, text="Message 2"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_messages.json")

            save_messages_to_json(messages, output_file, append=False)

            self.assertTrue(os.path.exists(output_file))

            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["message_id"], 1)
            self.assertEqual(data[1]["message_id"], 2)

    def test_save_messages_to_json_append(self):
        """Test appending messages to existing JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_messages.json")

            # Save initial messages
            messages1 = [MockMessage(id=1, text="Message 1")]
            save_messages_to_json(messages1, output_file, append=False)

            # Append new messages
            messages2 = [MockMessage(id=2, text="Message 2")]
            save_messages_to_json(messages2, output_file, append=True)

            # Verify both messages exist
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["message_id"], 1)
            self.assertEqual(data[1]["message_id"], 2)

    def test_save_messages_to_json_no_duplicates(self):
        """Test that duplicate messages are not added when appending."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_messages.json")

            # Save initial messages
            messages1 = [
                MockMessage(id=1, text="Message 1"),
                MockMessage(id=2, text="Message 2"),
            ]
            save_messages_to_json(messages1, output_file, append=False)

            # Try to append the same message
            messages2 = [MockMessage(id=1, text="Message 1 updated")]
            save_messages_to_json(messages2, output_file, append=True)

            # Verify no duplicates
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(len(data), 2)
            # Original message should still be there
            self.assertEqual(data[0]["message_id"], 1)
            self.assertEqual(data[0]["text"], "Message 1")

    def test_json_output_format(self):
        """Test that JSON output is properly formatted."""
        message = MockMessage(id=1, text="Test")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_messages.json")
            save_messages_to_json([message], output_file, append=False)

            # Read and verify JSON is valid and formatted
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Should have indentation (2 spaces)
            self.assertIn("  ", content)
            # Should be valid JSON
            data = json.loads(content)
            self.assertIsInstance(data, list)
            self.assertIsInstance(data[0], dict)


if __name__ == "__main__":
    unittest.main()
