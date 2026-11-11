
import os
import mimetypes
import logging
from pathlib import Path
from urllib.parse import quote

from config import StudioConfig
from net import request


logger = logging.getLogger(__name__)


class StudioToolsLibrary:
    """
    Studio AI Tools Library

    Manages external tools and cloud storage
    for the AI video production studio.
    """

    def __init__(self):
        self.enabled_tools = [
            "supabase_cloud_uploader"
        ]

        logger.info(
            "StudioToolsLibrary initialized successfully"
        )

    def list_tools(self):
        """Return available tools."""
        return self.enabled_tools.copy()

    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check whether a tool is enabled."""
        return tool_name in self.enabled_tools

    async def upload_to_cloud_storage(
        self,
        file_path: str,
        task_id: str
    ):
        """
        Upload a generated file to Supabase Storage.

        Supports:
        - Videos
        - Images
        - Audio
        - Documents

        Returns the public URL when successful.
        """

        # Check Supabase configuration
        supabase_url = getattr(
            StudioConfig,
            "SUPABASE_URL",
            None
        )

        supabase_key = getattr(
            StudioConfig,
            "SUPABASE_KEY",
            None
        )

        bucket = getattr(
            StudioConfig,
            "SUPABASE_BUCKET",
            None
        )

        if not all([
            supabase_url,
            supabase_key,
            bucket
        ]):
            logger.warning(
                "Supabase configuration missing. "
                "Cloud upload skipped."
            )
            return None

        # Validate file
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        if not task_id:
            raise ValueError(
                "task_id cannot be empty"
            )

        # Detect content type
        content_type, _ = mimetypes.guess_type(
            str(path)
        )

        if not content_type:
            content_type = "application/octet-stream"

        # Generate safe storage name
        safe_task_id = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in str(task_id)
        )

        filename = (
            f"{safe_task_id}{path.suffix.lower()}"
        )

        encoded_bucket = quote(
            str(bucket),
            safe=""
        )

        encoded_filename = quote(
            filename,
            safe=""
        )

        base_url = supabase_url.rstrip("/")

        upload_url = (
            f"{base_url}/storage/v1/object/"
            f"{encoded_bucket}/{encoded_filename}"
        )

        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": content_type,
            "x-upsert": "true"
        }

        logger.info(
            "Uploading file to Supabase: %s",
            filename
        )

        try:
            with path.open("rb") as file:
                data = file.read()

            status, response = await request(
                "POST",
                upload_url,
                headers,
                data,
                timeout=180
            )

            if status not in (200, 201):
                raise RuntimeError(
                    f"Supabase upload failed. "
                    f"HTTP {status}: "
                    f"{str(response)[:300]}"
                )

            public_url = (
                f"{base_url}/storage/v1/object/"
                f"public/{encoded_bucket}/"
                f"{encoded_filename}"
            )

            logger.info(
                "File uploaded successfully: %s",
                filename
            )

            return public_url

        except Exception:
            logger.exception(
                "Cloud upload failed for task: %s",
                task_id
            )
            raise
