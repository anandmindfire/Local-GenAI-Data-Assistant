"""Ollama low-level client and health check utilities."""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def check_ollama_health() -> tuple[bool, dict[str, bool]]:
    """Check connectivity to Ollama and verify if required models are available.

    Returns:
        (is_online, {"chat_model_available": bool, "embedding_model_available": bool})
    """
    model_status = {
        "chat_model_available": False,
        "embedding_model_available": False,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code != 200:
                logger.warning(f"Ollama returned HTTP {resp.status_code}")
                return False, model_status

            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]

            # Check for chat model (matching exact or prefix)
            chat_target = settings.chat_model.split(":")[0]
            for m in models:
                if settings.chat_model in m or chat_target in m:
                    model_status["chat_model_available"] = True
                    break

            # Check for embedding model
            emb_target = settings.embedding_model.split(":")[0]
            for m in models:
                if settings.embedding_model in m or emb_target in m:
                    model_status["embedding_model_available"] = True
                    break

            return True, model_status
    except Exception as e:
        logger.warning(f"Failed to connect to Ollama at {settings.ollama_base_url}: {e}")
        return False, model_status
