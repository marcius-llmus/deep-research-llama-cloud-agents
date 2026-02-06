import logging
import os

from llama_cloud import AsyncLlamaCloud

logger = logging.getLogger(__name__)
agent_name = os.getenv("LLAMA_DEPLOY_DEPLOYMENT_NAME")
api_key = os.getenv("LLAMA_CLOUD_API_KEY")
base_url = os.getenv("LLAMA_CLOUD_BASE_URL")
project_id = os.getenv("LLAMA_DEPLOY_PROJECT_ID")


def get_llama_cloud_client() -> AsyncLlamaCloud:
    """Cloud services connection for file storage and processing."""
    return AsyncLlamaCloud(api_key=api_key, base_url=base_url)
