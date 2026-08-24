"""Generic S3-compatible object storage helpers."""

from typing import BinaryIO

import boto3

from app.core.config import settings


def get_object_storage_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.B2_ENDPOINT_URL,
        aws_access_key_id=settings.B2_KEY_ID,
        aws_secret_access_key=settings.B2_APPLICATION_KEY,
    )


def upload_object(
    key: str, body: bytes | BinaryIO, content_type: str | None = None
) -> str:
    params = {"Bucket": settings.B2_BUCKET_NAME, "Key": key, "Body": body}
    if content_type:
        params["ContentType"] = content_type
    get_object_storage_client().put_object(**params)
    return key


def generate_download_url(key: str, expires_in: int = 600) -> str:
    return get_object_storage_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.B2_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )


def delete_object(key: str) -> None:
    get_object_storage_client().delete_object(Bucket=settings.B2_BUCKET_NAME, Key=key)
