import logging
import tempfile
import os
from deep_research.clients import get_llama_cloud_client

logger = logging.getLogger(__name__)


class FileService:
    """
    Service for managing file uploads to LlamaCloud.
    Decoupled from parsing logic.
    """

    def __init__(self):
        self.client = get_llama_cloud_client()

    async def upload_bytes(self, content: bytes, filename: str) -> str:
        """Uploads raw bytes to LlamaCloud and returns the file_id."""
        if not content:
            raise ValueError("Content cannot be empty")

        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".tmp") as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name

        try:
            file_obj = await self.client.files.create(file=tmp_path, purpose="parse")
            return str(file_obj.id)
        except Exception as e:
            logger.error(f"Failed to upload bytes for {filename}: {e}")
            raise
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
