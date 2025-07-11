import asyncio
import aiobotocore
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

class S3Service:
    """
    Service class for interacting with AWS S3.
    Uses aiobotocore for asynchronous operations.
    """
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, aws_region: str, bucket_name: str):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = aws_region
        self.bucket_name = bucket_name

    async def _get_s3_client(self):
        """
        Asynchronously gets an S3 client session.
        """
        session = aiobotocore.get_session()
        return session.create_client(
            "s3",
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )

    async def upload_file(self, file_content: bytes, object_name: str, content_type: str = "application/octet-stream"):
        """
        Uploads a file to the S3 bucket.
        """
        async with await self._get_s3_client() as client:
            try:
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=file_content,
                    ContentType=content_type
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'AccessDenied':
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to S3 bucket. Check credentials and permissions.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 upload failed: {e}")
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during S3 upload: {e}")

    async def download_file(self, object_name: str):
        """
        Downloads a file from the S3 bucket.
        Returns file content as bytes and content type.
        """
        async with await self._get_s3_client() as client:
            try:
                response = await client.get_object(Bucket=self.bucket_name, Key=object_name)
                async with response['Body'] as stream:
                    file_content = await stream.read()
                content_type = response.get('ContentType', 'application/octet-stream')
                return file_content, content_type
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{object_name}' not found in S3 bucket.")
                if e.response['Error']['Code'] == 'AccessDenied':
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to S3 bucket. Check credentials and permissions.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 download failed: {e}")
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during S3 download: {e}")

    async def delete_file(self, object_name: str):
        """
        Deletes a file from the S3 bucket.
        """
        async with await self._get_s3_client() as client:
            try:
                await client.delete_object(Bucket=self.bucket_name, Key=object_name)
            except ClientError as e:
                if e.response['Error']['Code'] == 'AccessDenied':
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to S3 bucket. Check credentials and permissions.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 deletion failed: {e}")
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during S3 deletion: {e}")

    async def list_files(self, prefix: str = ""):
        """
        Lists all objects in the S3 bucket with an optional prefix.
        """
        async with await self._get_s3_client() as client:
            try:
                response = await client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
                files = [content['Key'] for content in response.get('Contents', [])]
                return files
            except ClientError as e:
                if e.response['Error']['Code'] == 'AccessDenied':
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to S3 bucket. Check credentials and permissions.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"S3 list failed: {e}")
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during S3 list: {e}")