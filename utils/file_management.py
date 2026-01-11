"""Utility functions to handle downloaded files."""

import glob
import logging
import os
import pathlib
from hashlib import md5

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: str) -> str:
    """
    Calculate MD5 hash of file in chunks to avoid memory issues.

    Parameters
    ----------
    file_path: str
        Absolute path of the file to hash.

    Returns
    -------
    str
        Hexadecimal MD5 hash of the file.
    """
    hash_md5 = md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except IOError as e:
        logger.error(f"Cannot read file {file_path} for hashing: {e}")
        raise


def get_next_name(file_path: str) -> str:
    """
    Get next available name to download file.

    Parameters
    ----------
    file_path: str
        Absolute path of the file for which next available name to
        be generated.

    Returns
    -------
    str
        Absolute path of the next available name for the file.
    """
    posix_path = pathlib.Path(file_path)
    counter: int = 1
    new_file_name: str = os.path.join("{0}", "{1}-copy{2}{3}")
    while os.path.isfile(
        new_file_name.format(
            posix_path.parent,
            posix_path.stem,
            counter,
            "".join(posix_path.suffixes),
        )
    ):
        counter += 1
    return new_file_name.format(
        posix_path.parent,
        posix_path.stem,
        counter,
        "".join(posix_path.suffixes),
    )


def manage_duplicate_file(file_path: str) -> str:
    """
    Check if a file is duplicate.

    Compare the md5 of files with copy name pattern
    and remove if the md5 hash is same.

    Parameters
    ----------
    file_path: str
        Absolute path of the file for which duplicates needs to
        be managed.

    Returns
    -------
    str
        Absolute path of the duplicate managed file.
    """
    # Calculate current file hash using streaming
    try:
        current_file_md5: str = calculate_file_hash(file_path)
    except IOError:
        return file_path

    posix_path = pathlib.Path(file_path)
    file_base_name: str = "".join(posix_path.stem.split("-copy")[0])
    name_pattern: str = f"{posix_path.parent}/{file_base_name}*"
    # Reason for using `str.translate()`
    # https://stackoverflow.com/q/22055500/6730439
    old_files: list = glob.glob(
        name_pattern.translate({ord("["): "[[]", ord("]"): "[]]"})
    )
    if file_path in old_files:
        old_files.remove(file_path)

    # Check for duplicates with proper file handling
    for old_file_path in old_files:
        try:
            old_file_md5: str = calculate_file_hash(old_file_path)
        except IOError as e:
            logger.warning(f"Cannot read file {old_file_path}: {e}")
            continue

        if current_file_md5 == old_file_md5:
            try:
                os.remove(file_path)
                logger.info(f"Removed duplicate: {file_path}")
                return old_file_path
            except OSError as e:
                logger.error(f"Cannot remove file {file_path}: {e}")
                return file_path

    return file_path
