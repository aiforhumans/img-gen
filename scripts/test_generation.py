import urllib.request
import json
import time

payload = json.dumps({
    "prompt": "A cinematic photograph of an abandoned 1980s arcade at night, wet floor, neon signs saying ARCADE 84.",
    "model": "auto",
    "mode": "auto",
    "aspect_ratio": "16:9",
    "quality": "balanced",
    "steps": 10
}).encode("utf-8")

req = urllib.request.Request("http://127.0.0.1:7860/api/generate", data=payload, headers={"Content-Type": "application/json"})
resp = json.loads(urllib.request.urlopen(req).read().decode())
job_id = resp["job_id"]
print(f"Submitted job: {job_id}")

while True:
    time.sleep(0.3)
    status_req = urllib.request.urlopen(f"http://127.0.0.1:7860/api/jobs/{job_id}")
    job = json.loads(status_req.read().decode())
    state = job["state"]
    progress = job["progress"]
    curr_step = job["current_step"]
    tot_steps = job["total_steps"]
    print(f"State: {state} | Progress: {progress}% | Step: {curr_step}/{tot_steps}")
    if state in ["complete", "failed"]:
        print("\n--- Completed Job Summary ---")
        print(f"Model Used: {job['model']}")
        print(f"Routing Reason: {job['routing_reason']}")
        print(f"Resolution: {job['width']}x{job['height']}")
        print(f"Output File: {job['output_image_path']}")
        print(f"Total Time: {job['metrics']['total_time']}s")
        print(f"Peak VRAM: {job['metrics']['peak_vram_mb']} MB")
        break
