import json
from pathlib import Path

styles = [
    {
        "id": "photorealistic",
        "name": "Photorealistic",
        "category": "Photography",
        "prompt_template": "{prompt}, ultra-realistic, highly detailed skin texture, 8k uhd, dslr quality, soft natural lighting, high dynamic range",
        "negative_prompt": "deformed, distorted, disfigured, doll, plastic, cartoon, render, 3d, oversaturated, blurry",
        "recommended_aspect_ratio": "3:4",
        "recommended_model": "zimage-turbo",
        "default": True
    },
    {
        "id": "cinematic",
        "name": "Cinematic",
        "category": "Film",
        "prompt_template": "{prompt}, cinematic film still, 35mm photograph, anamorphic lens, dramatic lighting, volumetric atmosphere, shallow depth of field, color graded",
        "negative_prompt": "cheap video, amateur, overexposed, cartoon, flat lighting, watermark",
        "recommended_aspect_ratio": "16:9",
        "recommended_model": "flux-klein-4b"
    },
    {
        "id": "editorial_fashion",
        "name": "Editorial Fashion",
        "category": "Fashion",
        "prompt_template": "{prompt}, high fashion magazine editorial, vogue aesthetic, studio backdrop, dynamic pose, sharp focus, professional fashion photography, elegant styling",
        "negative_prompt": "casual snap, low quality, bad anatomy, blurry, artifacts",
        "recommended_aspect_ratio": "3:4",
        "recommended_model": "zimage-turbo"
    },
    {
        "id": "analog_film",
        "name": "Analog Film",
        "category": "Photography",
        "prompt_template": "{prompt}, vintage 35mm film photograph, kodak portra 400, warm film grain, subtle light leaks, retro tones, candid mood, timeless aesthetic",
        "negative_prompt": "digital crisp, sterile, 3d render, oversaturated, plastic skin",
        "recommended_aspect_ratio": "3:2",
        "recommended_model": "sdxl"
    },
    {
        "id": "anime",
        "name": "Anime & Manga",
        "category": "Art",
        "prompt_template": "{prompt}, modern anime artwork, makoto shinkai aesthetic, vibrant colors, detailed cel shading, clean lineart, luminous atmospheric lighting",
        "negative_prompt": "photorealistic, 3d render, western comic, lowres, grainy",
        "recommended_aspect_ratio": "16:9",
        "recommended_model": "flux-klein-4b"
    },
    {
        "id": "illustration",
        "name": "Digital Illustration",
        "category": "Art",
        "prompt_template": "{prompt}, expressive digital painting, painterly brush strokes, rich color palette, evocative composition, award winning artstation masterpiece",
        "negative_prompt": "photo, amateur sketch, muddy colors, harsh geometry",
        "recommended_aspect_ratio": "1:1",
        "recommended_model": "flux-klein-4b"
    },
    {
        "id": "concept_art",
        "name": "Concept Art",
        "category": "Art",
        "prompt_template": "{prompt}, epic video game concept art, sprawling world building, matte painting, immense scale, moody atmospheric haze, intricate environment details",
        "negative_prompt": "simple, cartoon, flat, bad perspective, watermark",
        "recommended_aspect_ratio": "21:9",
        "recommended_model": "flux-klein-9b"
    },
    {
        "id": "cyberpunk",
        "name": "Cyberpunk",
        "category": "Sci-Fi",
        "prompt_template": "{prompt}, cyberpunk city aesthetic, neon glowing highlights, rain-slicked asphalt, holographic interfaces, futuristic architecture, moody twilight",
        "negative_prompt": "sunny pastoral, historic, fantasy, low contrast",
        "recommended_aspect_ratio": "16:9",
        "recommended_model": "flux-klein-4b"
    },
    {
        "id": "dark_fantasy",
        "name": "Dark Fantasy",
        "category": "Fantasy",
        "prompt_template": "{prompt}, dark fantasy grim atmosphere, elden ring style, gothic architecture, haunting fog, muted color tones, ethereal rim light, sinister mystery",
        "negative_prompt": "cheerful, bright cartoon, saturated rainbow, cute",
        "recommended_aspect_ratio": "16:9",
        "recommended_model": "flux-klein-9b"
    },
    {
        "id": "product_photography",
        "name": "Product Photography",
        "category": "Commercial",
        "prompt_template": "{prompt}, commercial product photography, minimalist studio setup, clean softbox reflections, pristine details, premium catalog quality, neutral gradient background",
        "negative_prompt": "messy, dirty, noisy, blurry, distorted text, cheap",
        "recommended_aspect_ratio": "1:1",
        "recommended_model": "qwen-image"
    },
    {
        "id": "architecture",
        "name": "Architecture & Interiors",
        "category": "Architecture",
        "prompt_template": "{prompt}, architectural photography, archdaily feature, architectural digest interior, golden hour natural light, perfectly aligned vertical lines, modern minimalism",
        "negative_prompt": "crooked angles, cluttered, fisheye, distorted walls",
        "recommended_aspect_ratio": "16:9",
        "recommended_model": "flux-klein-4b"
    },
    {
        "id": "macro",
        "name": "Macro Photography",
        "category": "Photography",
        "prompt_template": "{prompt}, extreme macro photography, 100mm f/2.8 lens, microscopic details, crystalline clarity, razor sharp focal plane, creamy bokeh background",
        "negative_prompt": "wide shot, low resolution, flat, out of focus",
        "recommended_aspect_ratio": "1:1",
        "recommended_model": "zimage-turbo"
    },
    {
        "id": "portrait_studio",
        "name": "Portrait Studio",
        "category": "Photography",
        "prompt_template": "{prompt}, studio headshot portrait, rembrandt lighting, catching light in eyes, 85mm portrait lens, smooth skin texture, professional color grading",
        "negative_prompt": "bad eyes, extra fingers, cartoon, plastic, over-smoothed",
        "recommended_aspect_ratio": "3:4",
        "recommended_model": "zimage-turbo"
    }
]

out_dir = Path("config/styles")
out_dir.mkdir(parents=True, exist_ok=True)

for style in styles:
    file_path = out_dir / f"{style['id']}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(style, f, indent=2)
    print(f"Wrote {file_path}")

print(f"Successfully generated {len(styles)} style presets.")
