from typing import Literal
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Text-to-3D Generator")
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class GenerateRequest(BaseModel):
    prompt: str


class SceneSpec(BaseModel):
    shape: Literal["box", "sphere", "cylinder", "torus", "cone"]
    color: str
    scale: float
    title: str
    description: str


def build_scene_spec(prompt: str) -> SceneSpec:
    normalized_prompt = prompt.lower()

    if any(word in normalized_prompt for word in ["car", "truck", "vehicle"]):
        shape = "box"
        color = "#e63946"
    elif any(word in normalized_prompt for word in ["ball", "planet", "globe", "sphere"]):
        shape = "sphere"
        color = "#4cc9f0"
    elif any(word in normalized_prompt for word in ["tree", "tower", "rocket", "cylinder"]):
        shape = "cylinder"
        color = "#2a9d8f"
    elif any(word in normalized_prompt for word in ["ring", "donut", "torus"]):
        shape = "torus"
        color = "#f4a261"
    elif any(word in normalized_prompt for word in ["pyramid", "cone"]):
        shape = "cone"
        color = "#9b5de5"
    else:
        shape = "sphere"
        color = "#f15bb5"

    scale = max(0.8, min(2.2, 0.8 + len(prompt.split()) * 0.12))

    return SceneSpec(
        shape=shape,
        color=color,
        scale=round(scale, 2),
        title=f"Generated {shape}",
        description=f"Backend mapped '{prompt}' to a {shape} scene object.",
    )

# Allow local development and same-origin frontend access.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate")
def generate_model(request: GenerateRequest):
    print(f"Received prompt: {request.prompt}")
    scene = build_scene_spec(request.prompt)
    return {
        "message": "Generation request received",
        "prompt": request.prompt,
        "scene": scene.model_dump(),
    }


if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
