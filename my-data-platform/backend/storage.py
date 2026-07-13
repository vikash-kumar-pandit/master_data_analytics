# backend/storage.py
import os
import uuid
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

S3_ENDPOINT = os.getenv("S3_ENDPOINT", None)
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "datasaas-uploads")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION
)


def init_s3():
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
    except ClientError:
        try:
            s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
            print(f"Bucket '{S3_BUCKET_NAME}' created successfully.")
        except Exception as e:
            print(f"Failed to create bucket: {e}")


def upload_stream_to_s3(file: UploadFile) -> str:
    file_key = f"uploads/{uuid.uuid4()}-{file.filename}"
    s3_client.upload_fileobj(
        file.file,
        S3_BUCKET_NAME,
        file_key
    )
    return file_key


def get_file_bytes_from_s3(file_key: str) -> bytes:
    response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=file_key)
    return response['Body'].read()
