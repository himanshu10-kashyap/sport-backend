import asyncio
import importlib
import logging
import os
import uuid
from pathlib import Path

import boto3


logger = logging.getLogger(__name__)


ALLOWED_MIME_TYPES = {
    "image/jpeg": "images",
    "image/png": "images",
    "image/webp": "images",
    "image/gif": "images",
    # Voice
    "audio/mpeg": "voices",
    "audio/mp4": "voices",
    "audio/ogg": "voices",
    "audio/wav": "voices",
    "audio/webm": "voices",
    # Video
    "video/mp4": "videos",
    "video/quicktime": "videos",
    "video/webm": "videos",
    "video/x-m4v": "videos",
    "video/mpeg": "videos",

    "application/pdf": "documents",
    "application/vnd.ms-excel": "excels",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excels",
    "text/csv": "excels",
}

MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB

_s3_client = None


def get_s3():
    """Build the client on first use.

    Creating it at import time made this module unusable unless .env had
    already been loaded by an earlier import, because the credentials are
    read from the environment here.
    """
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
    return _s3_client


def _is_nsfw(file_bytes: bytes) -> bool:
    """Optional - the detector and its heavy deps (torch/timm/PIL) are not
    installed in every environment. Skipped silently rather than failing the
    upload."""
    for module_path in ("utils.nsfw_detector", "src.utils.nsfw_detector"):
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            continue
        try:
            return module.is_nsfw_image(file_bytes, threshold=0.4)
        except Exception as e:
            logger.warning("NSFW check failed, allowing upload: %s", e)
            return False
    logger.info("NSFW detector not installed, skipping check")
    return False


def _cloudfront_base() -> str:
    """The configured value is often a bare host, but every stored URL has
    to be absolute or the frontend cannot load it."""
    base = (os.getenv("AWS_CLOUDFRONT_URL") or "").strip().rstrip("/")
    if not base:
        raise ValueError("AWS_CLOUDFRONT_URL is not configured")
    if not base.startswith(("http://", "https://")):
        base = f"https://{base}"
    return base


def _resolve_upload(file, folder):
    """Validate the type, then pick the destination prefix.

    The mime check must run even when a folder override is given, otherwise
    passing folder= silently turns off validation and any file type lands in
    the bucket.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise ValueError("Unsupported file type")
    return folder or ALLOWED_MIME_TYPES[file.content_type]


def upload_file_to_s3(file, user_id=None, folder=None) -> str:
    resolved_folder = _resolve_upload(file, folder)

    original_name = file.filename or "upload"
    ext = Path(original_name).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"

    key = (
        f"{resolved_folder}/{user_id}/{filename}"
        if user_id
        else f"{resolved_folder}/{filename}"
    )

    file_bytes = file.file.read()

    if not file_bytes:
        raise ValueError("Uploaded file is empty")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("File size must not exceed 500 MB")

    if resolved_folder == "images" and _is_nsfw(file_bytes):
        raise ValueError("NSFW image detected. Upload rejected.")

    get_s3().put_object(
        Bucket=os.getenv("AWS_S3_BUCKET_NAME"),
        Key=key,
        Body=file_bytes,
        ContentType=file.content_type,
        CacheControl=(
            "public, max-age=31536000"
            if resolved_folder == "images"
            else "no-cache"
        ),
    )

    return f"{_cloudfront_base()}/{key}"


async def upload_file_to_s3_async(file, user_id=None, folder=None) -> str:
    """Async wrapper: read the upload with await and push to S3 off-loop."""
    resolved_folder = _resolve_upload(file, folder)

    original_name = file.filename or "upload"
    ext = Path(original_name).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    key = (
        f"{resolved_folder}/{user_id}/{filename}"
        if user_id
        else f"{resolved_folder}/{filename}"
    )

    file_bytes = await file.read()
    if not file_bytes:
        raise ValueError("Uploaded file is empty")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("File size must not exceed 500 MB")

    if resolved_folder == "images" and _is_nsfw(file_bytes):
        raise ValueError("NSFW image detected. Upload rejected.")

    await asyncio.to_thread(
        get_s3().put_object,
        Bucket=os.getenv("AWS_S3_BUCKET_NAME"),
        Key=key,
        Body=file_bytes,
        ContentType=file.content_type,
        CacheControl=(
            "public, max-age=31536000"
            if resolved_folder == "images"
            else "no-cache"
        ),
    )

    return f"{_cloudfront_base()}/{key}"


def delete_file_from_s3(photo_url: str):
    try:
        cloudfront_base = _cloudfront_base()
        key = photo_url.replace(f"{cloudfront_base}/", "", 1)

        get_s3().delete_object(
            Bucket=os.getenv("AWS_S3_BUCKET_NAME"),
            Key=key
        )
    except Exception as e:
        print(f"S3 delete failed for {photo_url}: {e}")


async def delete_file_from_s3_async(photo_url: str):
    try:
        cloudfront_base = _cloudfront_base()
        key = photo_url.replace(f"{cloudfront_base}/", "", 1)

        await asyncio.to_thread(
            get_s3().delete_object,
            Bucket=os.getenv("AWS_S3_BUCKET_NAME"),
            Key=key,
        )
    except Exception as e:
        print(f"S3 delete failed for {photo_url}: {e}")


def get_s3_key_from_url(file_url: str) -> str:
    """
    Convert CloudFront URL into S3 object key.
    """

    cloudfront_base = _cloudfront_base()

    if not file_url.startswith(cloudfront_base + "/"):
        raise ValueError("Invalid CloudFront URL")

    return file_url.replace(cloudfront_base + "/", "", 1)
