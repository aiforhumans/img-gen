import re
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.app.core.logger import app_logger

class RoutingDecision(BaseModel):
    task: str                          # "text_to_image", "image_to_image", "image_editing", "inpainting", "outpainting"
    category: str                      # "photorealism", "typography", "creative_concept", "portrait", "scifi", "general"
    text_rendering: bool               # True if in-image typography/signs detected
    editing: bool                      # True if instruction edit detected
    model: str                         # "flux-klein-4b", "flux-klein-9b", "zimage-turbo", "qwen-image", "sdxl"
    width: int                         # Suggested width
    height: int                        # Suggested height
    steps: int                         # Suggested steps
    guidance: float                    # Suggested guidance
    aspect_ratio: str                  # "1:1", "16:9", "9:16", "3:4", "21:9"
    seed: int                          # -1 for random
    reason: str                        # Human-readable explanation of why this model was chosen

class AutoRouter:
    """
    Intelligent prompt analyzer and model selector.
    Evaluates prompt intent, style cues, text rendering needs,
    and aspect ratios to choose the optimal generation engine.
    """
    def __init__(self):
        # Photographic / portrait indicators
        self.portrait_patterns = [
            r"\b(portrait|headshot|face|woman|man|person|girl|boy|model|fashion|studio lighting|rembrandt|bokeh|close-up|eyes|skin)\b"
        ]
        self.photorealism_patterns = [
            r"\b(photograph|photo|photorealistic|raw photo|dslr|35mm|canon|nikon|film grain|hyperrealistic|candid photo|snapshot)\b"
        ]

        # Typography / signs / text in image
        self.typography_patterns = [
            r'["\']([^"\']{2,30})["\']', # Text inside quotes
            r"\b(saying|text|words|letters|sign|poster|typography|logo|reads|labeled|billboard|neon sign saying)\b"
        ]

        # Editing instructions
        self.edit_patterns = [
            r"^(change|replace|remove|add|make|turn|modify|edit)\b",
            r"\b(change\s+.+\s+to\s+|remove\s+the\s+|make\s+her\s+|make\s+his\s+|replace\s+with)\b"
        ]

        # SDXL legacy / specific LoRA patterns
        self.sdxl_patterns = [
            r"\b(sdxl|civitai|lora:|vintage anime|checkpoint|controlnet)\b"
        ]

        # High-complexity / ultra-quality cues
        self.high_quality_patterns = [
            r"\b(masterpiece|highly detailed|complex|massive|sprawling|8k uhd|intricate|epic scale|floating cities|cinematic universe)\b"
        ]

    def analyze(self, prompt: str, user_mode: str = "auto", has_input_image: bool = False, enforce_installed: bool = False) -> RoutingDecision:
        p_lower = prompt.lower()

        # 1. Detect Editing vs Text-to-Image
        is_editing = False
        if has_input_image or any(re.search(pat, p_lower) for pat in self.edit_patterns):
            is_editing = True

        # 2. Detect Typography / In-image Text & Photographic Patterns
        has_text = any(re.search(pat, prompt) for pat in self.typography_patterns)
        is_portrait = any(re.search(pat, p_lower) for pat in self.portrait_patterns)
        is_photo = any(re.search(pat, p_lower) for pat in self.photorealism_patterns)

        # 3. Detect Aspect Ratio Cues from Prompt
        ar = "1:1"
        w, h = 1024, 1024
        if re.search(r"\b(landscape|16:9|widescreen|cinematic|panoramic|wallpaper)\b", p_lower):
            ar = "16:9"
            w, h = 1280, 720
        elif re.search(r"\b(portrait|vertical|9:16|phone wallpaper|story|reel)\b", p_lower):
            ar = "9:16"
            w, h = 720, 1280
        elif re.search(r"\b(cinema|ultrawide|21:9|movie still)\b", p_lower):
            ar = "21:9"
            w, h = 1344, 576
        elif re.search(r"\b(3:4|headshot|magazine)\b", p_lower):
            ar = "3:4"
            w, h = 896, 1152

        # 4. Mode Overrides (if user explicitly selected a non-auto Mode in UI)
        if user_mode == "photo":
            res = RoutingDecision(
                task="text_to_image",
                category="photorealism",
                text_rendering=has_text,
                editing=False,
                model="zimage-turbo",
                width=w if ar != "1:1" else 896,
                height=h if ar != "1:1" else 1152,
                steps=8,
                guidance=1.5,
                aspect_ratio="3:4" if ar == "1:1" else ar,
                seed=-1,
                reason="User explicitly selected 'Photo' mode: routed to Z-Image Turbo for fast photographic realism."
            )
            return self._resolve_available_model(res) if enforce_installed else res
        elif user_mode == "design":
            res = RoutingDecision(
                task="text_to_image",
                category="typography",
                text_rendering=True,
                editing=False,
                model="qwen-image",
                width=w,
                height=h,
                steps=25,
                guidance=5.0,
                aspect_ratio=ar,
                seed=-1,
                reason="User explicitly selected 'Design' mode: routed to Qwen Image for precision layout and text rendering."
            )
            return self._resolve_available_model(res) if enforce_installed else res
        elif user_mode == "creative":
            res = RoutingDecision(
                task="text_to_image",
                category="creative_concept",
                text_rendering=has_text,
                editing=False,
                model="flux-klein-9b",
                width=w,
                height=h,
                steps=28,
                guidance=3.5,
                aspect_ratio=ar,
                seed=-1,
                reason="User explicitly selected 'Creative' mode: routed to FLUX.2 Klein 9B for maximum artistic fidelity."
            )
            return self._resolve_available_model(res) if enforce_installed else res
        elif user_mode == "edit" or is_editing:
            res = RoutingDecision(
                task="image_editing" if has_input_image else "text_to_image",
                category="editing",
                text_rendering=has_text,
                editing=True,
                model="qwen-image",
                width=w,
                height=h,
                steps=25,
                guidance=5.0,
                aspect_ratio=ar,
                seed=-1,
                reason="Detected instruction-based editing intent: routed to Qwen Image instruction editing engine."
            )
            return self._resolve_available_model(res) if enforce_installed else res

        decision = None
        # Case A: SDXL triggers or explicit SDXL LoRA
        if any(re.search(pat, p_lower) for pat in self.sdxl_patterns):
            decision = RoutingDecision(
                task="text_to_image",
                category="legacy_sdxl",
                text_rendering=has_text,
                editing=False,
                model="sdxl",
                width=w,
                height=h,
                steps=25,
                guidance=7.0,
                aspect_ratio=ar,
                seed=-1,
                reason="Detected SDXL checkpoint or SDXL LoRA keywords: routed to Stable Diffusion XL legacy engine."
            )

        # Case B: Typography, Signs, Posters, or Quoted Text
        elif has_text:
            decision = RoutingDecision(
                task="text_to_image",
                category="typography",
                text_rendering=True,
                editing=False,
                model="qwen-image",
                width=w,
                height=h,
                steps=25,
                guidance=5.0,
                aspect_ratio=ar,
                seed=-1,
                reason="Detected signs, posters, or quotes in prompt: routed to Qwen Image for crisp typographic accuracy."
            )

        # Case C: Portraits, People, and Photographic Realism
        elif is_portrait and is_photo:
            decision = RoutingDecision(
                task="text_to_image",
                category="photorealism",
                text_rendering=False,
                editing=False,
                model="zimage-turbo",
                width=896 if ar == "1:1" else w,
                height=1152 if ar == "1:1" else h,
                steps=8,
                guidance=1.5,
                aspect_ratio="3:4" if ar == "1:1" else ar,
                seed=-1,
                reason="Prompt requests realistic portrait photography: routed to Z-Image Turbo (8-step fast photorealism)."
            )
        elif is_portrait:
            decision = RoutingDecision(
                task="text_to_image",
                category="portrait",
                text_rendering=False,
                editing=False,
                model="zimage-turbo",
                width=896 if ar == "1:1" else w,
                height=1152 if ar == "1:1" else h,
                steps=8,
                guidance=1.5,
                aspect_ratio="3:4" if ar == "1:1" else ar,
                seed=-1,
                reason="Prompt focuses on human portraits: routed to Z-Image Turbo for realistic anatomy and skin tones."
            )

        # Case D: Epic Scale / High Quality Fantasy or Concept Art
        elif any(re.search(pat, p_lower) for pat in self.high_quality_patterns):
            decision = RoutingDecision(
                task="text_to_image",
                category="creative_concept",
                text_rendering=False,
                editing=False,
                model="flux-klein-9b",
                width=w,
                height=h,
                steps=28,
                guidance=3.5,
                aspect_ratio=ar,
                seed=-1,
                reason="Prompt contains complex world-building or high-detail fantasy: routed to FLUX.2 Klein 9B high-quality engine."
            )

        # Case E: Default General-Purpose Modern Diffusion Engine
        else:
            decision = RoutingDecision(
                task="text_to_image",
                category="general",
                text_rendering=False,
                editing=False,
                model="flux-klein-4b",
                width=w,
                height=h,
                steps=20,
                guidance=3.5,
                aspect_ratio=ar,
                seed=-1,
                reason="General creative scene: routed to FLUX.2 Klein 4B default fast diffusion engine."
            )

        return self._resolve_available_model(decision) if enforce_installed else decision

    def _resolve_available_model(self, decision: RoutingDecision) -> RoutingDecision:
        try:
            from backend.app.models.registry import model_registry
            installed = [mid for mid, adapter in model_registry.adapters.items() if adapter.has_weights()]
            if installed and decision.model not in installed:
                preferred = "zimage-turbo" if "zimage-turbo" in installed else ("sdxl" if "sdxl" in installed else installed[0])
                orig_model = decision.model
                decision.model = preferred
                if preferred in ["zimage-turbo", "sdxl"]:
                    decision.steps = 8
                    decision.guidance = 1.5
                decision.reason = f"Target model '{orig_model}' weights not downloaded. Auto-routed to installed '{preferred}' on RTX 5080. [Original: {decision.reason}]"
        except Exception:
            pass
        return decision

auto_router = AutoRouter()
