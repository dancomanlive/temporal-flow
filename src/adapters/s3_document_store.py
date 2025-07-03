"""S3 Document Store Adapter - Concrete implementation for AWS S3."""

from typing import Optional
import os
from urllib.parse import urlparse

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    # Mock classes for type hints when boto3 is not available
    class ClientError(Exception):
        pass
    class NoCredentialsError(Exception):
        pass

from src.ports.document_store import (
    DocumentStore, 
    Document, 
    DocumentNotFoundError, 
    DocumentAccessError
)


class S3DocumentStore(DocumentStore):
    """Concrete implementation of DocumentStore for AWS S3.
    
    This adapter implements the DocumentStore interface using boto3
    to interact with AWS S3 buckets.
    """
    
    def __init__(
        self, 
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1"
    ):
        """Initialize S3 client.
        
        Args:
            aws_access_key_id: AWS access key (if None, uses environment or IAM role)
            aws_secret_access_key: AWS secret key (if None, uses environment or IAM role)
            region_name: AWS region name
            
        Raises:
            DocumentAccessError: If boto3 is not available or credentials are invalid
        """
        if not BOTO3_AVAILABLE:
            raise DocumentAccessError("boto3 is required for S3DocumentStore. Install with: pip install boto3")
            
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY'),
                region_name=region_name
            )
        except NoCredentialsError as e:
            raise DocumentAccessError(f"AWS credentials not found: {e}")

    def _parse_s3_uri(self, source_uri: str) -> tuple[str, str]:
        """Parse S3 URI into bucket and key.
        
        Args:
            source_uri: S3 URI in format s3://bucket/key
            
        Returns:
            Tuple of (bucket_name, object_key)
            
        Raises:
            ValueError: If URI format is invalid
        """
        parsed = urlparse(source_uri)
        if parsed.scheme != 's3':
            raise ValueError(f"Invalid S3 URI scheme: {parsed.scheme}")
        
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        
        if not bucket or not key:
            raise ValueError(f"Invalid S3 URI format: {source_uri}")
            
        return bucket, key

    async def get_document(self, source_uri: str) -> Document:
        """Retrieve a document from S3.
        
        Args:
            source_uri: S3 URI (e.g., s3://bucket/path/to/file.txt)
            
        Returns:
            Document object with content and metadata
            
        Raises:
            DocumentNotFoundError: If the document doesn't exist
            DocumentAccessError: If access is denied or other retrieval error
        """
        try:
            bucket, key = self._parse_s3_uri(source_uri)
            
            # Get object
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            
            # Read content
            content = response['Body'].read()
            
            # Extract metadata
            metadata = {
                'etag': response.get('ETag', '').strip('"'),
                'last_modified': response.get('LastModified'),
                'content_length': response.get('ContentLength', 0),
                'storage_class': response.get('StorageClass', 'STANDARD'),
            }
            
            # Add custom metadata if present
            if 'Metadata' in response:
                metadata.update(response['Metadata'])
            
            return Document(
                source_uri=source_uri,
                content=content,
                metadata=metadata,
                content_type=response.get('ContentType', 'application/octet-stream'),
                size=response.get('ContentLength', 0),
                last_modified=response.get('LastModified').isoformat() if response.get('LastModified') else None
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise DocumentNotFoundError(f"Document not found: {source_uri}")
            elif error_code == 'NoSuchBucket':
                raise DocumentNotFoundError(f"Bucket not found in URI: {source_uri}")
            elif error_code in ['AccessDenied', 'Forbidden']:
                raise DocumentAccessError(f"Access denied to document: {source_uri}")
            else:
                raise DocumentAccessError(f"Error retrieving document {source_uri}: {e}")
        except ValueError as e:
            raise DocumentAccessError(f"Invalid URI format: {e}")
        except Exception as e:
            raise DocumentAccessError(f"Unexpected error retrieving document {source_uri}: {e}")

    async def list_documents(self, prefix: str = "", max_results: int = 100) -> list[str]:
        """List documents in S3 bucket.
        
        Args:
            prefix: S3 prefix to filter documents (format: s3://bucket/prefix)
            max_results: Maximum number of document URIs to return
            
        Returns:
            List of S3 URIs
            
        Raises:
            DocumentAccessError: If listing fails
        """
        try:
            if prefix and prefix.startswith('s3://'):
                bucket, key_prefix = self._parse_s3_uri(prefix)
            else:
                # If no valid S3 URI prefix provided, return empty list
                return []
            
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=key_prefix,
                MaxKeys=max_results
            )
            
            uris = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    uri = f"s3://{bucket}/{obj['Key']}"
                    uris.append(uri)
            
            return uris
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise DocumentAccessError(f"Bucket not found: {bucket}")
            elif error_code in ['AccessDenied', 'Forbidden']:
                raise DocumentAccessError(f"Access denied to bucket: {bucket}")
            else:
                raise DocumentAccessError(f"Error listing documents: {e}")
        except ValueError as e:
            raise DocumentAccessError(f"Invalid prefix format: {e}")
        except Exception as e:
            raise DocumentAccessError(f"Unexpected error listing documents: {e}")

    async def document_exists(self, source_uri: str) -> bool:
        """Check if a document exists in S3.
        
        Args:
            source_uri: S3 URI to check
            
        Returns:
            True if document exists, False otherwise
        """
        try:
            bucket, key = self._parse_s3_uri(source_uri)
            
            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['NoSuchKey', 'NoSuchBucket', '404']:
                return False
            else:
                # For access denied or other errors, we can't determine existence
                raise DocumentAccessError(f"Error checking document existence {source_uri}: {e}")
        except ValueError:
            # Invalid URI format
            return False
        except Exception as e:
            raise DocumentAccessError(f"Unexpected error checking document existence {source_uri}: {e}")
