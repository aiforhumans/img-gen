import re
from typing import Dict, Any, List, Optional

class LocalPromptAnalyzer:
    """
    Local rule-based prompt analysis and enhancement engine.
    Analyzes subject, style, photographic vs artistic intent,
    and enriches short prompts without altering core meaning.
    """
    def __init__(self):
        self.subjects = [
            "woman", "man", "person", "cat", "dog", "car", "building", "landscape",
            "robot", "dragon", "forest", "city", "arcade", "room", "sword", "castle"
        ]
        self.photo_keywords = [
            "photo", "photograph", "cinematic", "film", "dslr", "35mm", "lens",
            "bokeh", "studio lighting", "portrait", "candid", "kodak"
        ]
        self.art_keywords = [
            "illustration", "painting", "anime", "manga", "concept art",
            "digital art", "drawing", "sketch", "oil painting", "watercolor"
        ]
        self.negative_patterns = [
            r"\bwithout\s+([a-zA-Z\s]+)",
            r"\bno\s+([a-zA-Z\s]+)",
            r"\bavoid\s+([a-zA-Z\s]+)"
        ]

    def analyze(self, prompt: str) -> Dict[str, Any]:
        p_lower = prompt.lower()

        # Subject extraction
        found_subjects = []
        for s in self.subjects:
            if re.search(rf"\b{s}\b", p_lower):
                found_subjects.append(s)

        # Style classification
        is_photo = any(kw in p_lower for kw in self.photo_keywords)
        is_art = any(kw in p_lower for kw in self.art_keywords)
        style = "photographic" if is_photo else ("artistic" if is_art else "general")

        # Negative concepts detection
        negatives = []
        for pat in self.negative_patterns:
            matches = re.findall(pat, p_lower)
            for m in matches:
                negatives.append(m.strip())

        # Quality hints
        wants_high_quality = any(k in p_lower for k in ["masterpiece", "8k", "highly detailed", "intricate"])

        return {
            "raw_prompt": prompt,
            "detected_subjects": found_subjects,
            "detected_style": style,
            "is_photographic": is_photo,
            "extracted_negatives": negatives,
            "wants_high_quality": wants_high_quality,
            "word_count": len(prompt.split())
        }

    def enhance(self, prompt: str, style_preset: Optional[str] = None) -> str:
        """
        Enhances short prompts by adding aesthetic descriptors
        while strictly preserving user's core intent.
        """
        analysis = self.analyze(prompt)
        words = prompt.strip().split()

        # If prompt is already detailed (>20 words), do not over-expand
        if len(words) >= 20:
            return prompt

        additions = []
        if analysis["is_photographic"]:
            if "lighting" not in prompt.lower():
                additions.append("natural atmospheric lighting")
            if "depth" not in prompt.lower():
                additions.append("subtle depth of field")
            additions.append("sharp focus, fine textural detail")
        elif analysis["detected_style"] == "artistic":
            additions.append("masterful composition, vibrant balanced colors, high aesthetic quality")
        else:
            additions.append("detailed environment, clean composition, cohesive color harmony")

        enhanced = f"{prompt.strip()}, {', '.join(additions)}"
        return enhanced

local_analyzer = LocalPromptAnalyzer()
