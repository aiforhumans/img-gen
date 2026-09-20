import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.app.core.config import PROJECT_ROOT
from backend.app.core.logger import app_logger

class StyleComposition(BaseModel):
    original_prompt: str
    style_id: str
    style_prompt: str
    negative_prompt: str
    recommended_aspect_ratio: Optional[str] = None
    recommended_model: Optional[str] = None

class StyleComposer:
    def __init__(self, styles_dir: Optional[Path] = None):
        self.styles_dir = styles_dir or (PROJECT_ROOT / "config" / "styles")
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.reload_styles()

    def reload_styles(self):
        self._cache.clear()
        if self.styles_dir.exists():
            for f in self.styles_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        sid = data.get("id", f.stem)
                        self._cache[sid] = data
                except Exception as e:
                    app_logger.warning(f"Error loading style preset {f}: {e}")

    def get_style(self, style_id: str) -> Optional[Dict[str, Any]]:
        if not self._cache:
            self.reload_styles()
        return self._cache.get(style_id)

    def compose(
        self,
        prompt: str,
        style_id: Optional[str] = None,
        user_negative_prompt: str = ""
    ) -> StyleComposition:
        clean_prompt = prompt.strip()
        if not style_id or style_id.lower() in ["none", "default", "custom", ""]:
            return StyleComposition(
                original_prompt=clean_prompt,
                style_id="none",
                style_prompt=clean_prompt,
                negative_prompt=user_negative_prompt.strip()
            )

        style_data = self.get_style(style_id)
        if not style_data:
            return StyleComposition(
                original_prompt=clean_prompt,
                style_id=style_id,
                style_prompt=clean_prompt,
                negative_prompt=user_negative_prompt.strip()
            )

        template = style_data.get("prompt_template", "{prompt}")
        if "{prompt}" in template:
            style_prompt = template.replace("{prompt}", clean_prompt)
        else:
            style_prompt = f"{clean_prompt}, {template}"

        # Combine negative prompts avoiding duplicate clauses
        style_neg = style_data.get("negative_prompt", "").strip()
        user_neg = user_negative_prompt.strip()

        combined_neg_parts = []
        if user_neg:
            combined_neg_parts.append(user_neg)
        if style_neg and style_neg not in user_neg:
            combined_neg_parts.append(style_neg)

        combined_neg = ", ".join(combined_neg_parts)

        return StyleComposition(
            original_prompt=clean_prompt,
            style_id=style_id,
            style_prompt=style_prompt,
            negative_prompt=combined_neg,
            recommended_aspect_ratio=style_data.get("recommended_aspect_ratio"),
            recommended_model=style_data.get("recommended_model")
        )

style_composer = StyleComposer()
