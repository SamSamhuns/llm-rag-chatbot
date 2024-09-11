"""
Common utils
"""
import os
import time
import hashlib
import logging
import functools
import urllib.request as urllib2
from typing import Callable, Union

logger = logging.getLogger("timeit_decorator")


def timeit_decorator(func: Callable):
    """
    prints the function runtime in seconds
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t_0 = time.time()
        result = func(*args, **kwargs)
        t_1 = time.time()
        call_time_msg = f"function {func.__name__} call time {t_1 - t_0:.3f}s"
        logger.info(call_time_msg)
        return result
    return wrapper


def get_mode_ext(mode: str):
    """
    Returns the file extension for the given mode.
    mode (str): The mode, either "image" or "video".
    Returns: The file extension (str), either ".jpg" or ".mp4".
    """
    return {"image": ".jpg", "video": ".mp4"}[mode]


def remove_file(path: str) -> None:
    """
    Removes the file at the given path.
    path (str): The path to the file to remove.
    """
    if os.path.exists(path):
        os.remove(path)


async def download_url_file(download_url: str, download_path: str) -> None:
    """
    Downloads the file at the given URL to the given download path.
    download_url (str): The URL of the file to download.
    download_path (str): The path to download the file to.
    """
    response = urllib2.urlopen(download_url)
    with open(download_path, "wb") as f:
        f.write(response.read())


async def cache_file_locally(file_cache_path: str, data: bytes) -> None:
    """
    Writes the given data to a file at the given file cache path.
    file_cache_path (str): The path to cache the data to.
    data (bytes): The data to cache to a file.
    """
    with open(file_cache_path, "wb") as img_file_ptr:
        img_file_ptr.write(data)


def get_file_md5(file: Union[str, bytes], byte_chunk: int = 8192):
    """
    Calculates the MD5 hash of the file at the given path or using the file byte contents.
    file (Union[str, bytes]): The path to the file or the file contents as bytes.
    byte_chunk (int): size of bytes to read and update
    Returns: The MD5 hash of the file (str).
    """
    hash_md5 = hashlib.md5()
    if isinstance(file, str):    # if file is a filepath
        with open(file, "rb") as f_ptr:
            for chunk in iter(lambda: f_ptr.read(byte_chunk), b""):
                hash_md5.update(chunk)
    elif isinstance(file, bytes):  # if file is the file byte contents
        hash_md5.update(file)
    else:
        raise NotImplementedError(f"md5sum calc not supported for file type {file}")
    return hash_md5.hexdigest()
