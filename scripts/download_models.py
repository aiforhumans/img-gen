import sys
import argparse
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.downloader import model_downloader, MODEL_REPOSITORIES, get_hf_token, set_hf_token
from backend.app.core.config import settings

def main():
    parser = argparse.ArgumentParser(description="Download official model checkpoints for Antigravity Studio")
    parser.add_argument("--model", type=str, choices=list(MODEL_REPOSITORIES.keys()) + ["all"], help="Model ID to download")
    args = parser.parse_args()

    print("======================================================================")
    print("           ANTIGRAVITY DIFFUSION STUDIO - MODEL DOWNLOADER            ")
    print("======================================================================")
    print(f"Target Storage: {settings.paths.model_dirs[0]}\n")

    selected_model = args.model
    if not selected_model:
        print("Available Models:")
        for idx, (mid, info) in enumerate(MODEL_REPOSITORIES.items(), 1):
            status = model_downloader.get_status(mid)
            status_badge = "[INSTALLED]" if status["status"] == "complete" else "[NOT DOWNLOADED]"
            print(f"  {idx}. {mid:<14} {status_badge:<16} - {info['description']}")
        choices_map = {str(i): k for i, k in enumerate(MODEL_REPOSITORIES.keys(), 1)}
        all_choice_idx = str(len(choices_map) + 1)
        print(f"  {all_choice_idx}. all            Download all models")
        print("  0. Exit")

        try:
            choice = input(f"\nSelect a model number to download (0-{all_choice_idx}) [default: 1]: ").strip()
            if not choice: choice = "1"
            if choice == "0": return
            if choice == all_choice_idx:
                selected_model = "all"
            else:
                selected_model = choices_map.get(choice, "juggernaut-xl")
        except KeyboardInterrupt:
            return

    models_to_download = list(MODEL_REPOSITORIES.keys()) if selected_model == "all" else [selected_model]

    # Check Hugging Face authentication for gated models
    gated_requested = any("flux" in m for m in models_to_download)
    current_token = get_hf_token()
    if gated_requested and not current_token:
        print("\n----------------------------------------------------------------------")
        print("[NOTE] Official FLUX.1 models are gated by Black Forest Labs on HF.")
        print("       - If you have an HF Token (hf_...), enter it to use official repo.")
        print("       - OR press [ENTER] to automatically use the public un-gated mirror!")
        print("----------------------------------------------------------------------")
        try:
            tok = input("Hugging Face Access Token (optional, press Enter to skip): ").strip()
            if tok:
                set_hf_token(tok)
                print("[INFO] Token saved to config/hf_token.txt")
        except KeyboardInterrupt:
            return

    for mid in models_to_download:
        info = MODEL_REPOSITORIES[mid]
        print(f"\n>>> Starting download for: {mid} ({info['repo_id']})...")
        print(f"    Estimated Size: ~{info['estimated_size_gb']} GB")

        model_downloader.start_download(mid)

        # Track progress
        while True:
            time.sleep(1.0)
            status = model_downloader.get_status(mid)
            state = status["status"]
            dl_mb = status["downloaded_mb"]
            tot_mb = status["total_mb"]
            spd = status["speed_mbps"]

            if state == "downloading":
                sys.stdout.write(f"\r    Status: Downloading... {dl_mb:.1f} MB / {tot_mb:.1f} MB ({status['progress']:.1f}%) | Speed: {spd:.2f} MB/s")
                sys.stdout.flush()
            elif state == "complete":
                sys.stdout.write(f"\r    Status: [COMPLETE] Successfully downloaded {dl_mb:.1f} MB!                \n")
                sys.stdout.flush()
                break
            elif state == "failed":
                print(f"\n    [ERROR] Download failed: {status['error']}")
                break

    print("\n======================================================================")
    print("Downloads finished! Models are ready to use in the studio.")
    print("======================================================================")

if __name__ == "__main__":
    main()
