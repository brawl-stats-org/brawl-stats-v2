"""
R2 storage client with singleton pattern.
Handles file existence checks, downloads, and uploads.
"""

import os
import gzip
import json
from pathlib import Path
import boto3
from dotenv import load_dotenv

load_dotenv()


class R2Client:
    """Singleton R2 storage client"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.bucket = os.getenv('R2_BUCKET_NAME')
        self.client = boto3.client(
            's3',
            endpoint_url=os.getenv('R2_ENDPOINT'),
            aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY')
        )
        self._initialized = True

    def get_client(self):
        """Get the underlying boto3 client"""
        return self.client

    def get_bucket(self):
        """Get the R2 bucket name"""
        return self.bucket

    def file_exists(self, r2_key: str) -> bool:
        """Check if a file exists in R2 bucket

        Args:
            r2_key: R2 object key (e.g., 'raw/battlelogs/2026-09-06.json.gz')

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=r2_key)
            return True
        except:
            return False

    def download_file(self, r2_key: str, local_path: str, verbose: bool = False) -> bool:
        """Download a single file from R2 to local path

        Args:
            r2_key: R2 object key
            local_path: Local file path to save to
            verbose: Print download progress

        Returns:
            True if successful, False if file doesn't exist
        """
        if not self.file_exists(r2_key):
            if verbose:
                print(f"File not found in R2: {r2_key}")
            return False

        # Create parent directory if needed
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        if verbose:
            print(f"Downloading {r2_key} → {local_path}")

        self.client.download_file(self.bucket, r2_key, local_path)
        return True

    def download_gzip_json(self, r2_key: str, verbose: bool = False) -> dict | list | None:
        """Download and parse a gzipped JSON file from R2

        Args:
            r2_key: R2 object key (must be .json.gz)
            verbose: Print download progress

        Returns:
            Parsed JSON dict/list, or None if file doesn't exist
        """
        if not self.file_exists(r2_key):
            if verbose:
                print(f"File not found in R2: {r2_key}")
            return None

        if verbose:
            print(f"Downloading {r2_key} from R2")

        # Download to bytes
        response = self.client.get_object(Bucket=self.bucket, Key=r2_key)
        gzipped_data = response['Body'].read()

        # Decompress and parse
        decompressed = gzip.decompress(gzipped_data)
        return json.loads(decompressed.decode('utf-8'))

    def upload_file(self, local_path: str, r2_key: str, verbose: bool = False) -> bool:
        """Upload a single file from local to R2

        Args:
            local_path: Local file path
            r2_key: R2 object key destination
            verbose: Print upload progress

        Returns:
            True if successful, False if local file doesn't exist
        """
        if not os.path.exists(local_path):
            if verbose:
                print(f"Local file not found: {local_path}")
            return False

        if verbose:
            print(f"Uploading {local_path} → {r2_key}")

        self.client.upload_file(local_path, self.bucket, r2_key)
        return True

    def upload_directory(self, local_dir: str, r2_prefix: str, verbose: bool = False) -> int:
        """Upload all files from local directory to R2 with prefix

        Args:
            local_dir: Local directory path
            r2_prefix: Prefix for R2 keys (e.g., 'raw/battlelogs', 'artifacts')
            verbose: Print upload progress

        Returns:
            Number of files uploaded
        """
        local_path = Path(local_dir)
        if not local_path.exists():
            if verbose:
                print(f"Directory not found: {local_dir}")
            return 0

        files = list(local_path.rglob('*'))
        files = [f for f in files if f.is_file()]

        if not files:
            if verbose:
                print(f"No files found in {local_dir}")
            return 0

        uploaded = 0
        for file_path in files:
            rel_path = file_path.relative_to(local_path)
            r2_key = f"{r2_prefix}/{rel_path}".replace('\\', '/')

            if verbose:
                print(f"Uploading {file_path} → {r2_key}")

            self.client.upload_file(str(file_path), self.bucket, r2_key)
            uploaded += 1

        return uploaded
