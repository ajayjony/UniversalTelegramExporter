"""Downloads media from telegram."""

import asyncio
import logging
import os
import shutil
import random
import time
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple, Union

import yaml
from telethon import TelegramClient
from telethon.errors import FileReferenceExpiredError, BadRequestError
from telethon.tl.types import (
    Document,
    Message,
    MessageMediaDocument,
    MessageMediaPhoto,
    Photo,
)
from tqdm import tqdm

from utils.error_handler import ErrorHandler
from utils.file_management import get_next_name, manage_duplicate_file
from utils.logging_config import setup_logging, get_logger
from utils.config_manager import ConfigManager
from utils.message_export import save_messages_to_json
from utils.meta import APP_VERSION, DEVICE_MODEL, LANG_CODE, SYSTEM_VERSION, print_meta
from utils.models import DownloadSummary
from utils.state import DownloadState
from utils.updates import check_for_updates
from utils.validators import validate_chat_id, validate_api_id, validate_api_hash

# Initialize logging from configuration
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
setup_logging()
logger = get_logger(__name__)

# Constants
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5.0
MAX_RETRY_DELAY = 300.0
DEFAULT_PAGINATION_LIMIT = 100
MAX_CONCURRENT_DOWNLOADS = 5
CHUNK_SIZE_FOR_HASHING = 4096


def update_config(config: Dict, state: DownloadState) -> None:
    """
    Update existing configuration file.

    Preserves file structure and updates only changed values.
    Creates backups automatically before saving.

    Parameters
    ----------
    config: dict
        Configuration dict to be written into config file.
    state: DownloadState
        Current download state with failed and downloaded IDs.
    """
    # Calculate retry list from state
    updates = {
        "ids_to_retry": state.get_retry_ids(config.get("ids_to_retry", [])),
    }
    
    try:
        config_manager = ConfigManager(
            os.path.join(THIS_DIR, "config.yaml"), max_backups=5
        )
        config_manager.update_config(config, updates, create_backup=True)
        logger.info("Updated config file with new state")
    except IOError as e:
        logger.error(f"Failed to update config file: {e}")


def _can_download(_type: str, file_formats: Dict[str, List[str]], file_format: Optional[str]) -> bool:
    """
    Check if the given file format can be downloaded.

    Determines whether a file of the specified format should be downloaded
    based on the user's configured file format preferences.

    Parameters
    ----------
    _type : str
        Type of media object (e.g., 'audio', 'document', 'video', 'photo')
    file_formats : Dict[str, List[str]]
        Dictionary containing allowed file formats per media type.
        Keys are media types, values are lists of allowed formats or ['all']
    file_format : Optional[str]
        Format of the current file to be checked (e.g., 'mp3', 'pdf', 'mp4')

    Returns
    -------
    bool
        True if the file format can be downloaded, False otherwise

    Examples
    --------
    >>> file_formats = {'audio': ['mp3', 'ogg'], 'video': ['mp4']}
    >>> _can_download('audio', file_formats, 'mp3')
    True
    >>> _can_download('audio', file_formats, 'wav')
    False
    >>> _can_download('video', {'video': ['all']}, 'mkv')
    True
    """
    if _type in ["audio", "document", "video"]:
        if _type not in file_formats:
            return False
        allowed_formats: List[str] = file_formats[_type]
        if not isinstance(allowed_formats, list) or not allowed_formats:
            logger.warning(f"Invalid file_formats configuration for {_type}")
            return False
        if file_format not in allowed_formats and allowed_formats[0] != "all":
            return False
    return True


def _is_exist(file_path: str) -> bool:
    """
    Check if a file exists and it is not a directory.

    Verifies that the specified path points to an existing regular file
    (not a directory or symlink to a directory).

    Parameters
    ----------
    file_path : str
        Absolute or relative path to check

    Returns
    -------
    bool
        True if the file exists and is not a directory, False otherwise

    Examples
    --------
    >>> _is_exist('/path/to/existing/file.txt')
    True
    >>> _is_exist('/path/to/directory')
    False
    >>> _is_exist('/nonexistent/path')
    False
    """
    return not os.path.isdir(file_path) and os.path.exists(file_path)


def _progress_callback(current: int, total: int, pbar: tqdm) -> None:
    """
    Update progress bar for file downloads.

    Callback function that updates a tqdm progress bar with the current
    download progress. Handles cases where total size changes.

    Parameters
    ----------
    current : int
        Current number of bytes downloaded
    total : int
        Total number of bytes to download
    pbar : tqdm
        Progress bar instance to update with current progress

    Returns
    -------
    None

    Examples
    --------
    >>> from tqdm import tqdm
    >>> with tqdm(total=1024) as pbar:
    ...     _progress_callback(512, 1024, pbar)
    ...     _progress_callback(1024, 1024, pbar)
    """
    if pbar.total != total:
        pbar.total = total
        pbar.reset()
    pbar.update(current - pbar.n)


async def _get_media_meta(
    media_obj: Union[Document, Photo],
    _type: str,
    download_directory: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Extract file name and file format from media object.

    Determines the appropriate file path and format for a media object
    based on its type and attributes.

    Parameters
    ----------
    media_obj : Union[Document, Photo]
        The Telethon media object (Document or Photo)
    _type : str
        Type of media ('photo', 'video', 'audio', 'voice', 'video_note', 'document')
    download_directory : Optional[str]
        Custom directory path for downloads. If None, uses default structure
        relative to application directory

    Returns
    -------
    Tuple[str, Optional[str]]
        Tuple of (file_path, file_format) where file_format may be None for photos

    Examples
    --------
    >>> file_name, fmt = await _get_media_meta(photo_obj, 'photo')
    >>> file_name
    '/root/Output/photo/photo_12345.jpg'
    """
    file_format: Optional[str] = None
    if hasattr(media_obj, "mime_type") and media_obj.mime_type:
        file_format = media_obj.mime_type.split("/")[-1]
    elif _type == "photo":
        file_format = "jpg"

    # Determine base directory for downloads
    base_dir = download_directory if download_directory else THIS_DIR

    if _type in ["voice", "video_note"]:
        # Format timestamp to be Windows-safe by replacing colons with hyphens
        timestamp = media_obj.date.isoformat().replace(":", "-")
        file_name: str = os.path.join(
            base_dir,
            _type,
            f"{_type}_{timestamp}.{file_format}",
        )
    else:
        file_name_base = ""
        if hasattr(media_obj, "attributes"):
            for attr in media_obj.attributes:
                if hasattr(attr, "file_name"):
                    file_name_base = attr.file_name
                    break
        if file_name_base == "":
            if hasattr(media_obj, "id"):
                file_name_base = f"{_type}_{media_obj.id}"
        file_name = os.path.join(base_dir, _type, file_name_base)
    return file_name, file_format


def get_media_type(message: Message) -> Optional[str]:
    """
    Determine the media type from the message's media attributes.

    Analyzes a Telegram message to determine what type of media it contains
    by checking the media object type and document attributes. Handles
    special cases like voice notes and video notes that are stored as
    documents with specific attributes.

    Parameters
    ----------
    message : Message
        The Telethon message object to analyze

    Returns
    -------
    Optional[str]
        The media type as a string: 'photo', 'video', 'audio', 'voice',
        'video_note', 'document', or None if no media is present

    Examples
    --------
    >>> media_type = get_media_type(message)
    >>> if media_type == 'photo':
    ...     print("This message contains a photo")
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


async def download_media(  # pylint: disable=too-many-locals
    client: TelegramClient,
    message: Message,
    media_types: List[str],
    file_formats: Dict[str, List[str]],
    state: DownloadState,
    download_directory: Optional[str] = None,
    download_semaphore: Optional[asyncio.Semaphore] = None,
    error_handler: Optional[ErrorHandler] = None,
) -> int:
    """
    Download media from a Telegram message with retry logic.

    Downloads a single media file from a message if it matches configured
    type and format filters. Implements exponential backoff retry logic
    with automatic refetch for expired file references.

    Parameters
    ----------
    client : TelegramClient
        Connected Telethon client for downloading
    message : Message
        Message object containing media to download
    media_types : List[str]
        List of accepted media types to download.
        Supported: ['audio', 'document', 'photo', 'video', 'video_note', 'voice']
    file_formats : Dict[str, List[str]]
        Dictionary mapping media types to allowed format lists.
        Example: {'audio': ['mp3', 'ogg'], 'video': ['all']}
    state : DownloadState
        Download state tracker for marking success/failure
    download_directory : Optional[str]
        Custom output directory. If None, creates default structure
    download_semaphore : Optional[asyncio.Semaphore]
        Semaphore for rate limiting concurrent downloads
    error_handler : Optional[ErrorHandler]
        Error handler for user-friendly error messages

    Returns
    -------
    int
        The message ID (always returns, even if download fails)

    Examples
    --------
    >>> message_id = await download_media(
    ...     client, message, ['photo', 'video'],
    ...     {'photo': ['all'], 'video': ['mp4']},
    ...     state
    ... )
    """
    # Apply rate limiting if semaphore is provided
    if download_semaphore:
        async with download_semaphore:
            return await _download_media_internal(
                client, message, media_types, file_formats, state,
                download_directory, error_handler
            )
    else:
        return await _download_media_internal(
            client, message, media_types, file_formats, state,
            download_directory, error_handler
        )


async def _download_media_internal(
    client: TelegramClient,
    message: Message,
    media_types: List[str],
    file_formats: Dict[str, List[str]],
    state: DownloadState,
    download_directory: Optional[str] = None,
    error_handler: Optional[ErrorHandler] = None,
) -> int:
    """Internal download logic without rate limiting."""
    for retry in range(MAX_RETRIES):
        try:
            _type = get_media_type(message)
            logger.debug("Processing message %s of type %s", message.id, _type)
            if not _type or _type not in media_types:
                return message.id
            
            # Get the correct media object based on type
            if _type == "photo":
                media_obj = message.photo
            elif _type == "voice":
                media_obj = message.voice
            elif _type == "video_note":
                media_obj = message.video_note
            else:
                # For audio, video, document types
                media_obj = message.document
            
            if not media_obj:
                return message.id
            file_name, file_format = await _get_media_meta(
                media_obj, _type, download_directory
            )
            if _can_download(_type, file_formats, file_format):
                # Create progress bar for download
                file_size = getattr(media_obj, "size", 0)
                # Use original file name if available, otherwise generated name
                display_name = getattr(
                    media_obj, "file_name", os.path.basename(file_name)
                )
                desc = f"Downloading {display_name}"
                logger.info(desc)

                # Check if file exists and get next available name if needed
                if _is_exist(file_name):
                    file_name = get_next_name(file_name)

                # Download with progress bar
                with tqdm(
                    total=file_size, unit="B", unit_scale=True, desc=desc
                ) as pbar:
                    # pylint: disable=cell-var-from-loop
                    download_path = await client.download_media(
                        message,
                        file=file_name,
                        progress_callback=lambda c, t: _progress_callback(
                            c, t, pbar
                        ),
                    )
                    if download_path:
                        download_path = manage_duplicate_file(download_path)  # type: ignore

                if download_path and os.path.exists(download_path):
                    # Get actual file size after download
                    actual_file_size = os.path.getsize(download_path)
                    logger.info("Media downloaded - %s", download_path)
                    logger.debug("Successfully downloaded message %s", message.id)
                    state.mark_downloaded(message.id, actual_file_size)
                elif download_path:
                    # File was removed as duplicate, still mark as downloaded
                    state.mark_downloaded(message.id, file_size)
            break
        except FileReferenceExpiredError as e:
            if error_handler:
                error_handler.handle_error(e, message_id=message.id, logger=logger)
            else:
                logger.warning(
                    "Message[%d]: file reference expired (attempt %d/%d), refetching...",
                    message.id,
                    retry + 1,
                    MAX_RETRIES,
                )
            if retry < MAX_RETRIES - 1:
                try:
                    messages = await client.get_messages(message.chat.id, ids=message.id)
                    message = messages[0] if messages else message
                except Exception as refetch_error:
                    if error_handler:
                        error_handler.handle_error(refetch_error, message_id=message.id, logger=logger)
                    else:
                        logger.error(f"Cannot refetch message: {refetch_error}")
                    state.mark_failed(message.id)
                    return message.id
            else:
                if not error_handler:
                    logger.error(
                        "Message[%d]: file reference expired after retries, skipping.",
                        message.id,
                    )
                state.mark_failed(message.id)
        except TimeoutError as e:
            wait_time = min(MAX_RETRY_DELAY, (2 ** retry) * INITIAL_RETRY_DELAY + random.uniform(0, 1))
            if error_handler:
                error_handler.handle_error(e, message_id=message.id, logger=logger)
            else:
                logger.warning(
                    "Message[%d]: Timeout (attempt %d/%d). "
                    "Waiting %.1f seconds before retry...",
                    message.id,
                    retry + 1,
                    MAX_RETRIES,
                    wait_time,
                )
            if retry < MAX_RETRIES - 1:
                await asyncio.sleep(wait_time)
            else:
                if not error_handler:
                    logger.error(
                        "Message[%d]: Timeout after %d retries, skipping.",
                        message.id,
                        MAX_RETRIES,
                    )
                state.mark_failed(message.id)
        except BadRequestError as e:
            if error_handler:
                error_handler.handle_error(e, message_id=message.id, logger=logger)
            else:
                logger.error(f"Message[{message.id}]: Bad request - {e}")
            state.mark_failed(message.id)
            break
        except Exception as e:
            if error_handler:
                error_handler.handle_error(e, message_id=message.id, logger=logger, critical=True)
            else:
                logger.error(
                    f"Message[{message.id}]: Unexpected error: {type(e).__name__}: {e}",
                    exc_info=True,
                )
            state.mark_failed(message.id)
            break
    return message.id


async def process_messages(
    client: TelegramClient,
    messages: List[Message],
    media_types: List[str],
    file_formats: Dict[str, List[str]],
    state: DownloadState,
    download_directory: Optional[str] = None,
    export_file: Optional[str] = None,
    download_semaphore: Optional[asyncio.Semaphore] = None,
    error_handler: Optional[ErrorHandler] = None,
) -> int:
    """
    Process and download media from a batch of messages.

    Concurrently downloads media from multiple messages and optionally exports
    message metadata to JSON. Implements batch processing with progress tracking.

    Parameters
    ----------
    client : TelegramClient
        Connected Telethon client for downloading media
    messages : List[Message]
        List of Telegram message objects to process
    media_types : List[str]
        List of accepted media types to download.
        Supported: ['audio', 'document', 'photo', 'video', 'video_note', 'voice']
    file_formats : dict
        Dictionary mapping media types to allowed format lists.
        Example: {'audio': ['mp3', 'ogg'], 'video': ['all']}
    state : DownloadState
        Download state tracker for marking success/failure
    download_directory : Optional[str]
        Custom output directory for downloads. If None, uses default structure
    export_file : Optional[str]
        File path for JSON export of messages. If None, no export is performed

    Returns
    -------
    int
        Maximum message ID from the processed batch

    Notes
    -----
    Downloads are performed concurrently using asyncio.gather for efficiency.
    Message metadata is appended to existing JSON file if export_file is provided.

    Examples
    --------
    >>> message_ids = await process_messages(
    ...     client, messages, ['photo', 'video'],
    ...     {'photo': ['all'], 'video': ['mp4']},
    ...     state, export_file='./messages.json'
    ... )
    """
    message_ids = await asyncio.gather(
        *[
            download_media(
                client, message, media_types, file_formats, state,
                download_directory, download_semaphore, error_handler
            )
            for message in messages
        ]
    )
    logger.info("Processed batch of %d messages", len(messages))
    
    # Export messages to JSON if export_file is specified
    if export_file:
        save_messages_to_json(messages, export_file, append=True)
    
    last_message_id: int = max(message_ids)
    return last_message_id


def _parse_config_dates(config: Dict) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse start_date and end_date from configuration.

    Parameters
    ----------
    config : Dict
        Configuration dictionary

    Returns
    -------
    Tuple[Optional[datetime], Optional[datetime]]
        Parsed start_date and end_date with timezone info
    """
    start_date_val = config.get("start_date")
    if isinstance(start_date_val, str) and start_date_val.strip():
        start_date = datetime.fromisoformat(start_date_val)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
    elif isinstance(start_date_val, date):
        start_date = datetime.combine(
            start_date_val, datetime.min.time(), tzinfo=timezone.utc
        )
    else:
        start_date = None
    logger.info("Start date filter: %s", start_date or "None")

    end_date_val = config.get("end_date")
    if isinstance(end_date_val, str) and end_date_val.strip():
        end_date = datetime.fromisoformat(end_date_val)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
    elif isinstance(end_date_val, date):
        end_date = datetime.combine(
            end_date_val, datetime.min.time(), tzinfo=timezone.utc
        )
    else:
        end_date = None
    logger.info("End date filter: %s", end_date or "None")

    return start_date, end_date


def _setup_download_directory(config: Dict) -> Optional[str]:
    """
    Setup and validate download directory from configuration.

    Parameters
    ----------
    config : Dict
        Configuration dictionary

    Returns
    -------
    Optional[str]
        Absolute path to download directory, or None for default

    Raises
    ------
    PermissionError
        If directory is not writable
    """
    download_directory_val = config.get("download_directory")
    if isinstance(download_directory_val, str) and download_directory_val.strip():
        download_directory = download_directory_val.strip()
        # Convert to absolute path if relative
        if not os.path.isabs(download_directory):
            download_directory = os.path.abspath(download_directory)
        # Create directory if it doesn't exist
        os.makedirs(download_directory, exist_ok=True)
        # Check write permissions
        if not os.access(download_directory, os.W_OK):
            raise PermissionError(f"Cannot write to download directory: {download_directory}")
        logger.info("Custom download directory: %s", download_directory)
        return download_directory
    else:
        logger.info("Download directory: Default")
        return None


def _setup_export_file(config: Dict, download_directory: Optional[str]) -> Optional[str]:
    """
    Setup message export file path from configuration.

    Parameters
    ----------
    config : Dict
        Configuration dictionary
    download_directory : Optional[str]
        Download directory path

    Returns
    -------
    Optional[str]
        Absolute path to export file, or None if export disabled
    """
    export_messages_val = config.get("export_messages")
    if not export_messages_val:
        return None

    export_file_val = config.get("export_messages_file")
    if isinstance(export_file_val, str) and export_file_val.strip():
        export_file = export_file_val.strip()
        # Convert to absolute path if relative
        if not os.path.isabs(export_file):
            export_file = os.path.join(download_directory or THIS_DIR, export_file)
        logger.info("Message export file: %s", export_file)
    else:
        # Use default filename if not specified
        export_file = os.path.join(download_directory or THIS_DIR, "messages_export.json")
        logger.info("Message export file: %s (default)", export_file)

    return export_file


async def _setup_telegram_client(
    api_id: int, api_hash: str, config: Dict, output_dir: str
) -> TelegramClient:
    """
    Create and start Telegram client.

    Parameters
    ----------
    api_id : int
        Telegram API ID
    api_hash : str
        Telegram API hash
    config : Dict
        Configuration dictionary (for proxy settings)
    output_dir : str
        Directory for session file

    Returns
    -------
    TelegramClient
        Started Telegram client
    """
    proxy = config.get("proxy")
    proxy_dict = None
    if proxy:
        proxy_dict = {
            "proxy_type": proxy["scheme"],
            "addr": proxy["hostname"],
            "port": proxy["port"],
            "username": proxy.get("username"),
            "password": proxy.get("password"),
        }
    client = TelegramClient(
        os.path.join(output_dir, "user"),
        api_id=api_id,
        api_hash=api_hash,
        proxy=proxy_dict,
        device_model=DEVICE_MODEL,
        system_version=SYSTEM_VERSION,
        app_version=APP_VERSION,
        lang_code=LANG_CODE,
    )
    await client.start()
    return client


async def begin_import(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    config: Dict, pagination_limit: int
) -> Tuple[Dict, DownloadSummary]:
    """
    Create Telethon client and initiate media download from Telegram.

    Establishes connection to Telegram using provided credentials, iterates through
    messages in the specified chat, and downloads media files according to user
    configuration. Supports date filtering, file format filtering, and retry logic.

    Parameters
    ----------
    config : dict
        Configuration dictionary containing:
        - api_id: Telegram API ID
        - api_hash: Telegram API hash
        - chat_id: Chat/channel to download from
        - last_read_message_id: Message ID to resume from
        - media_types: List of types to download
        - file_formats: Allowed formats per type
        - Optional: start_date, end_date, max_messages, download_directory
    pagination_limit : int
        Number of messages to process in each batch

    Returns
    -------
    Tuple[dict, DownloadSummary]
        Updated configuration and download session summary

    Raises
    ------
    FileNotFoundError
        If Telegram session cannot be created
    ValueError
        If configuration values are invalid

    Examples
    --------
    >>> config = {'api_id': 123456, 'api_hash': '...', ...}
    >>> config_updated, summary = await begin_import(config, 100)
    >>> summary.print_summary()
    """
    session_start_time = time.time()
    
    # Create Output folder if it doesn't exist
    output_dir = os.path.join(THIS_DIR, "Output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Validate configuration values
    try:
        api_id = validate_api_id(config.get("api_id"))
        api_hash = validate_api_hash(config.get("api_hash"))
        chat_id = validate_chat_id(config.get("chat_id"))
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    # Setup Telegram client
    client = await _setup_telegram_client(api_id, api_hash, config, output_dir)
    
    # Initialize download state and error handler
    state = DownloadState()
    error_handler = ErrorHandler()
    
    # Parse configuration
    last_read_message_id: int = config["last_read_message_id"]
    start_date, end_date = _parse_config_dates(config)
    
    max_messages_val = config.get("max_messages")
    if isinstance(max_messages_val, int):
        max_messages = max_messages_val
    elif isinstance(max_messages_val, str) and max_messages_val.strip():
        max_messages = int(max_messages_val)
    else:
        max_messages = None
    logger.info("Max messages to download: %s", max_messages or "Unlimited")
    
    # Setup download directory and export file
    download_directory = _setup_download_directory(config)
    export_file = _setup_export_file(config, download_directory)
    
    # Create rate limiting semaphore
    download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    
    messages_iter = client.iter_messages(
        chat_id, min_id=last_read_message_id + 1, reverse=True
    )
    messages_list: List[Message] = []
    pagination_count: int = 0
    total_messages: int = 0
    skipped_messages: int = 0
    
    # Process retry messages first
    if config["ids_to_retry"]:
        logger.info("Downloading files failed during last run...")
        skipped_messages_list: List[Message] = await client.get_messages(  # type: ignore
            chat_id, ids=config["ids_to_retry"]
        )
        for message in skipped_messages_list:
            pagination_count += 1
            messages_list.append(message)

    # Process messages with progress indicator
    with tqdm(desc="Processing messages", unit="msg") as pbar:
        async for message in messages_iter:  # type: ignore
            total_messages += 1
            pbar.update(1)
            
            if end_date and message.date > end_date:
                skipped_messages += 1
                continue
            if start_date and message.date < start_date:
                break
            if pagination_count != pagination_limit:
                pagination_count += 1
                messages_list.append(message)
            else:
                last_read_message_id = await process_messages(
                    client,
                    messages_list,
                    config["media_types"],
                    config["file_formats"],
                    state,
                    download_directory,
                    export_file,
                    download_semaphore,
                    error_handler,
                )
                if max_messages and len(state.downloaded_ids) >= max_messages:
                    break
                pagination_count = 0
                messages_list = []
                messages_list.append(message)
                config["last_read_message_id"] = last_read_message_id
                # Only update config periodically to reduce I/O
                if len(state.downloaded_ids) % 50 == 0:
                    update_config(config, state)
    
    # Process remaining messages
    if messages_list:
        last_read_message_id = await process_messages(
            client,
            messages_list,
            config["media_types"],
            config["file_formats"],
            state,
            download_directory,
            export_file,
            download_semaphore,
            error_handler,
        )

    await client.disconnect()
    config["last_read_message_id"] = last_read_message_id
    update_config(config, state)
    
    # Create summary using state's total_size_bytes
    session_duration = time.time() - session_start_time
    summary = DownloadSummary(
        total_messages=total_messages,
        successful_downloads=len(state.downloaded_ids),
        failed_downloads=len(state.failed_ids),
        skipped_messages=skipped_messages,
        total_size_bytes=state.total_size_bytes,
        duration_seconds=session_duration,
    )
    
    # Log error summary if errors occurred
    if error_handler:
        error_summary = error_handler.get_summary()
        if "No errors" not in error_summary:
            logger.info(error_summary)
    
    return config, summary


def main():
    """
    Main entry point for the Universal Telegram Exporter.

    Loads configuration, initiates download session, displays results summary,
    and checks for application updates.

    Raises
    ------
    FileNotFoundError
        If configuration file is not found
    ValueError
        If configuration values are invalid
    """
    try:
        config_manager = ConfigManager(
            os.path.join(THIS_DIR, "config.yaml"), max_backups=5
        )
        config = config_manager.load_config()
        
        # Get pagination limit from config or use default
        pagination_limit = config.get("pagination_limit", DEFAULT_PAGINATION_LIMIT)
        
        # Run the import with summary
        updated_config, summary = asyncio.get_event_loop().run_until_complete(
            begin_import(config, pagination_limit=pagination_limit)
        )
        
        # Display summary
        summary.print_summary()
        
        # Log summary details
        logger.info(f"Download session complete: {summary}")
        
        failed_count = len(updated_config.get("ids_to_retry", []))
        if failed_count:
            logger.info(
                "Downloading of %d files failed. "
                "Failed message ids are added to config file.\n"
                "These files will be downloaded on the next run.",
                failed_count,
            )
        
        check_for_updates()
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    print_meta(logger)
    main()
