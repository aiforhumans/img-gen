import httpx
from typing import Dict, Any, List, Optional
from backend.app.core.config import settings
from backend.app.core.logger import app_logger
from backend.app.prompt_engine.local_analyzer import local_analyzer

class LMStudioClient:
    """
    Optional client for local LM Studio API (http://127.0.0.1:1234/v1).
    Leveraged for deep prompt decomposition and expansion.
    Completely non-blocking and fallback-safe.
    """
    def __init__(self, base_url: str = "http://127.0.0.1:1234/v1"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=10.0)

    async def is_available(self) -> bool:
        try:
            resp = await self.client.get(f"{self.base_url}/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        try:
            resp = await self.client.get(f"{self.base_url}/models")
            if resp.status_code == 200:
                data = resp.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            app_logger.debug(f"LM Studio query models error: {e}")
        return []

    async def enhance_prompt(self, prompt: str, style_name: Optional[str] = None) -> str:
        """
        Enhances prompt using local LM Studio model if reachable,
        otherwise falls back seamlessly to rule-based LocalPromptAnalyzer.
        """
        if not settings.lm_studio.enabled:
            return local_analyzer.enhance(prompt)

        try:
            models = await self.list_models()
            if not models:
                return local_analyzer.enhance(prompt)

            target_model = models[0] # Use active/first model in LM Studio
            system_msg = (
                "You are an expert AI image prompt engineer. Expand the user's image prompt "
                "with vivid visual details, atmosphere, lighting, and composition while strictly "
                "preserving their core subject, style, and intent. "
                "Output ONLY the improved image prompt. Do not add quotes, introductions, or conversational text."
            )

            payload = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"Improve this prompt: {prompt}"}
                ],
                "temperature": 0.7,
                "max_tokens": 150
            }

            resp = await self.client.post(f"{self.base_url}/chat/completions", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                enhanced = data["choices"][0]["message"]["content"].strip()
                # Clean up any surrounding quotes or markdown
                enhanced = enhanced.strip('"\'`')
                if len(enhanced) > len(prompt):
                    app_logger.info(f"LM Studio enhanced prompt: '{enhanced}'")
                    return enhanced

        except Exception as e:
            app_logger.debug(f"LM Studio enhancement failed, falling back to local analyzer: {e}")

        return local_analyzer.enhance(prompt)

lm_studio_client = LMStudioClient()
