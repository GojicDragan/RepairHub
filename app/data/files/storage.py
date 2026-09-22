"""Privater S3-Adapter; weder Objekt-URLs noch Zugangsdaten verlassen den Server."""

import re

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

OBJECT_KEY = re.compile(r"images/[a-f0-9]{32}(?:-thumb)?\.webp\Z")


class ObjectStorage:
    def __init__(self, endpoint, region, bucket, access_key, secret_key):
        self.bucket = bucket
        self.options = {
            "endpoint_url": endpoint,
            "region_name": region,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "config": Config(
                signature_version="s3v4",
                # Interner Docker-Hostname statt eigener DNS-Namen pro Bucket.
                s3={"addressing_style": "path"},
                connect_timeout=3,
                read_timeout=10,
                retries={"total_max_attempts": 2},
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            ),
        }

    def client(self):
        # Ohne explizite Schlüssel niemals implizit EC2-/AWS-Zugangsdaten suchen.
        if not self.options["aws_access_key_id"] or not self.options["aws_secret_access_key"]:
            raise OSError("storage_unavailable")
        return boto3.client("s3", **self.options)

    def put(self, key, content, content_type):
        if not OBJECT_KEY.fullmatch(key):
            raise ValueError("invalid_object_key")
        try:
            self.client().put_object(
                Bucket=self.bucket, Key=key, Body=content, ContentType=content_type
            )
        except (BotoCoreError, ClientError):
            raise OSError("storage_unavailable") from None

    def read(self, key):
        if not OBJECT_KEY.fullmatch(key):
            raise ValueError("invalid_object_key")
        try:
            response = self.client().get_object(Bucket=self.bucket, Key=key)
            with response["Body"] as stream:
                # Ein zusätzliches Byte erkennt Übergrösse ohne unbeschränktes Einlesen.
                data = stream.read(10 * 1024 * 1024 + 1)
            if len(data) > 10 * 1024 * 1024:
                raise OSError("storage_unavailable")
            return data
        except (BotoCoreError, ClientError):
            raise OSError("storage_unavailable") from None
