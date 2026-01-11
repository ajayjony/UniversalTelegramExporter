"""Input validation utilities for configuration and user inputs."""

from typing import Union


def validate_chat_id(chat_id: Union[str, int]) -> Union[str, int]:
    """
    Validate and normalize chat_id input.

    Supports multiple formats for chat_id input:
    - Integer: 123456 (direct Telegram ID)
    - Username string: "@channel_name" or "channel_name"
    - Group ID: -1001234567890 (negative integers for groups)

    Parameters
    ----------
    chat_id : Union[str, int]
        The chat ID to validate, can be integer or string format

    Returns
    -------
    Union[str, int]
        Validated and normalized chat_id

    Raises
    ------
    ValueError
        If chat_id is invalid or malformed

    Examples
    --------
    >>> validate_chat_id(123456)
    123456

    >>> validate_chat_id("@my_channel")
    'my_channel'

    >>> validate_chat_id("-1001234567890")
    -1001234567890
    """
    if isinstance(chat_id, int):
        if chat_id == 0:
            raise ValueError("chat_id cannot be 0")
        return chat_id

    if isinstance(chat_id, str):
        chat_id = chat_id.strip()

        if not chat_id:
            raise ValueError("chat_id cannot be empty")

        # If it's a username
        if chat_id.startswith("@"):
            username = chat_id[1:]  # Remove @ prefix
            if not username:
                raise ValueError("Username cannot be empty after @")
            return username

        # Check if it looks like a username (no special chars except underscore)
        if not chat_id.startswith("-") and not chat_id.isdigit():
            # It's a username without @
            return chat_id

        # Try to convert to int (for numeric IDs or negative group IDs)
        try:
            int_id = int(chat_id)
            if int_id == 0:
                raise ValueError("chat_id cannot be 0")
            return int_id
        except ValueError as e:
            if "cannot be 0" in str(e):
                raise
            raise ValueError(f"Invalid chat_id format: {chat_id}") from e

    raise ValueError(f"chat_id must be int or str, got {type(chat_id).__name__}")


def validate_api_id(api_id: Union[str, int]) -> int:
    """
    Validate Telegram API ID.

    Parameters
    ----------
    api_id : Union[str, int]
        The API ID, should be a positive integer

    Returns
    -------
    int
        Validated API ID

    Raises
    ------
    ValueError
        If API ID is invalid
    """
    try:
        if isinstance(api_id, str):
            api_id = int(api_id)

        if not isinstance(api_id, int) or api_id <= 0:
            raise ValueError("api_id must be a positive integer")

        return api_id
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid api_id: {api_id}") from e


def validate_api_hash(api_hash: str) -> str:
    """
    Validate Telegram API hash.

    Parameters
    ----------
    api_hash : str
        The API hash string

    Returns
    -------
    str
        Validated API hash

    Raises
    ------
    ValueError
        If API hash is invalid
    """
    if not isinstance(api_hash, str):
        raise ValueError(f"api_hash must be string, got {type(api_hash).__name__}")

    api_hash = api_hash.strip()

    if not api_hash:
        raise ValueError("api_hash cannot be empty")

    if len(api_hash) < 20:
        raise ValueError("api_hash appears to be invalid (too short)")

    # API hash should be hexadecimal
    try:
        int(api_hash, 16)
    except ValueError:
        raise ValueError("api_hash should be hexadecimal string")

    return api_hash
