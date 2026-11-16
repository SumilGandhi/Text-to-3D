
import os
import uuid
import threading
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import torch
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.shap_e_generator import generate_3d


app = FastAPI(title="Local Shap-E AI Server")

# Security: set this environment variable before starting the server.
API_SECRET = os.getenv("LOCAL_AI_SECRET")

OUTPUT_DIR = Path(__file__).resolve().parent / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# One GPU generation at a time.
executor = ThreadPoolExecutor(max_workers=1)

jobs = {}
jobs_lock = threading.Lock()


class GenerateRequest(BaseModel):
    prompt: str


def check_secret(token: str | None):
    if not API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LOCAL_AI_SECRET is not configured."
        )

    if token != API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


def run_generation(job_id: str, prompt: str):
    with jobs_lock:
        jobs[job_id]["status"] = "processing"

    try:
        generated_path = generate_3d(prompt)

        source_path = Path(generated_path)
        result_path = OUTPUT_DIR / f"{job_id}.glb"

        # Copy the completed model to a unique job-specific filename.
        result_path.write_bytes(source_path.read_bytes())

        with jobs_lock:
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result_file"] = str(result_path)

    except Exception as error:
        traceback.print_exc()

        with jobs_lock:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(error)


@app.get("/health")
def health():
    return {
        "status": "online",
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": (
            torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else None
        )
    }


@app.post("/generate")
def start_generation(
    request: GenerateRequest,
    x_api_secret: str | None = Header(default=None)
):
    check_secret(x_api_secret)

    prompt = request.prompt.strip()

    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")

    job_id = str(uuid.uuid4())

    with jobs_lock:
        jobs[job_id] = {
            "status": "queued",
            "prompt": prompt
        }

    executor.submit(run_generation, job_id, prompt)

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Generation job submitted."
    }


@app.get("/status/{job_id}")
def generation_status(
    job_id: str,
    x_api_secret: str | None = Header(default=None)
):
    check_secret(x_api_secret)

    with jobs_lock:
        job = jobs.get(job_id)

        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")

        return {
            "job_id": job_id,
            "status": job["status"],
            "error": job.get("error")
        }


@app.get("/result/{job_id}")
def generation_result(
    job_id: str,
    x_api_secret: str | None = Header(default=None)
):
    check_secret(x_api_secret)

    with jobs_lock:
        job = jobs.get(job_id)

        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")

        if job["status"] != "completed":
            raise HTTPException(
                status_code=409,
                detail="Generation is not completed."
            )

        result_path = Path(job["result_file"])

    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Generated file not found.")

    return FileResponse(
        result_path,
        media_type="model/gltf-binary",
        filename=f"{job_id}.glb"
    )
