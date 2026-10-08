from pathlib import Path
import os
import re
import json
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
app = FastAPI(title="Text-to-3D Generator")
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
TRIPO_API_URL = "https://api.tripo3d.ai/v2/openapi"
MESHY_API_URL = "https://api.meshy.ai/openapi/v2"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class GenerateRequest(BaseModel):
    prompt: str
    enhance_prompt: bool = False


class TripoTaskRequest(BaseModel):
    task_id: str


def configured_api_key(name: str, placeholder: str) -> str:
    api_key = os.getenv(name)
    if not api_key or api_key == placeholder:
        raise HTTPException(
            status_code=503,
            detail=f"{name} is not configured. Add it to the project .env file.",
        )
    return api_key


async def enhance_prompt_with_openai(prompt: str) -> str:
    api_key = configured_api_key("OPENAI_API_KEY", "your_openai_api_key_here")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "temperature": 0.4,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Improve a text-to-3D prompt. Return only one concise visual description "
                    "of the object, including useful shape, material, color, and style details. "
                    "Do not add multiple objects or explanations."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(OPENAI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        detail = error.response.text[:500] or "OpenAI rejected the prompt enhancement request."
        raise HTTPException(status_code=502, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Could not reach OpenAI.") from error

    try:
        result = response.json()
        enhanced = result["choices"][0]["message"]["content"].strip()
    except (json.JSONDecodeError, KeyError, IndexError, AttributeError) as error:
        raise HTTPException(status_code=502, detail="OpenAI returned an invalid response.") from error
    if not enhanced:
        raise HTTPException(status_code=502, detail="OpenAI returned an empty enhanced prompt.")
    return enhanced


class SceneSpec(BaseModel):
    shape: Literal["box", "sphere", "cylinder", "torus", "cone"]
    object_type: str
    color: str
    scale: float
    title: str
    description: str


CSS_COLOR_NAMES = set(
    """
    aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond
    blue blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue
    cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey
    darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon
    darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet
    deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen
    fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew
    hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon
    lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey
    lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey
    lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine
    mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen
    mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite
    navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise
    palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red
    rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue
    slateblue slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise
    violet wheat white whitesmoke yellow yellowgreen
    """.split()
)
COLOR_PATTERN = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|rgba?\(\s*[^)]+\)",
    re.IGNORECASE,
)


def extract_color(prompt: str) -> str:
    coded_color = COLOR_PATTERN.search(prompt)
    if coded_color:
        return coded_color.group(0)

    words = re.findall(r"[a-zA-Z]+", prompt.lower())
    for index in range(len(words) - 1):
        compound_name = f"{words[index]}{words[index + 1]}"
        if compound_name in CSS_COLOR_NAMES:
            return compound_name
    for word in words:
        if word in CSS_COLOR_NAMES:
            return word
    return "#f15bb5"


def build_scene_spec(prompt: str) -> SceneSpec:
    normalized_prompt = prompt.lower()
    color = extract_color(prompt)
    if any(word in normalized_prompt for word in ["truck", "lorry", "pickup"]):
        shape, object_type = "box", "truck"
    elif any(word in normalized_prompt for word in ["sniper", "rifle"]):
        shape, object_type = "box", "sniper"
    elif any(word in normalized_prompt for word in ["pistol", "handgun", "gun"]):
        shape, object_type = "box", "pistol"
    elif any(word in normalized_prompt for word in ["bus", "coach"]):
        shape, object_type = "box", "bus"
    elif any(word in normalized_prompt for word in ["motorcycle", "motorbike", "bike"]):
        shape, object_type = "cylinder", "motorcycle"
    elif any(word in normalized_prompt for word in ["car", "vehicle", "sedan", "suv"]):
        shape, object_type = "box", "car"
    elif any(word in normalized_prompt for word in ["airplane", "aircraft", "jet", "plane"]):
        shape, object_type = "cone", "airplane"
    elif any(word in normalized_prompt for word in ["boat", "ship", "yacht"]):
        shape, object_type = "box", "boat"
    elif any(word in normalized_prompt for word in ["flower", "plant"]):
        shape, object_type = "cylinder", "flower"
    elif any(word in normalized_prompt for word in ["chair", "seat"]):
        shape, object_type = "box", "chair"
    elif any(word in normalized_prompt for word in ["table", "desk"]):
        shape, object_type = "box", "table"
    elif any(word in normalized_prompt for word in ["lamp", "light"]):
        shape, object_type = "cylinder", "lamp"
    elif "tree" in normalized_prompt:
        shape, object_type = "cylinder", "tree"
    elif any(word in normalized_prompt for word in ["rocket", "spaceship"]):
        shape, object_type = "cone", "rocket"
    elif any(word in normalized_prompt for word in ["house", "home", "building"]):
        shape, object_type = "box", "house"
    elif any(word in normalized_prompt for word in ["robot", "android"]):
        shape, object_type = "box", "robot"
    elif any(word in normalized_prompt for word in ["ball", "planet", "globe", "sphere"]):
        shape, object_type = "sphere", "sphere"
    elif any(word in normalized_prompt for word in ["tree", "tower", "rocket", "cylinder"]):
        shape, object_type = "cylinder", "cylinder"
    elif any(word in normalized_prompt for word in ["ring", "donut", "torus"]):
        shape, object_type = "torus", "torus"
    elif any(word in normalized_prompt for word in ["pyramid", "cone"]):
        shape, object_type = "cone", "cone"
    else:
        shape, object_type = "sphere", "sphere"

    scale = max(0.8, min(2.2, 0.8 + len(prompt.split()) * 0.12))
    return SceneSpec(
        shape=shape,
        object_type=object_type,
        color=color,
        scale=round(scale, 2),
        title=f"Generated {object_type}",
        description=f"Free local preview mapped '{prompt}' to a {object_type} scene object.",
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate")
async def generate_model(request: GenerateRequest):
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")
    generated_prompt = await enhance_prompt_with_openai(prompt) if request.enhance_prompt else prompt
    return {
        "message": "Generation completed",
        "prompt": prompt,
        "generated_prompt": generated_prompt,
        "scene": build_scene_spec(generated_prompt).model_dump(),
    }


@app.post("/generate/tripo")
async def generate_with_tripo(request: GenerateRequest):
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")

    api_key = os.getenv("TRIPO_API_KEY")
    if not api_key or api_key == "your_tripo_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="TRIPO_API_KEY is not configured. Add it to the project .env file.",
        )

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"type": "text_to_model", "prompt": prompt}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{TRIPO_API_URL}/task",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        detail = error.response.text[:500] or "Tripo rejected the request."
        raise HTTPException(status_code=502, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Could not reach Tripo AI.") from error

    try:
        result = response.json()
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=502, detail="Tripo returned an invalid JSON response.") from error
    task_id = result.get("data", {}).get("task_id")
    if not task_id:
        raise HTTPException(status_code=502, detail="Tripo returned no task ID.")
    return {"task_id": task_id, "provider": "Tripo AI", "prompt": prompt}


@app.get("/generate/tripo/status/{task_id}")
@app.get("/generate/tripo/{task_id}")
async def get_tripo_task(task_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", task_id):
        raise HTTPException(status_code=422, detail="Invalid Tripo task ID.")

    api_key = os.getenv("TRIPO_API_KEY")
    if not api_key or api_key == "your_tripo_api_key_here":
        raise HTTPException(status_code=503, detail="TRIPO_API_KEY is not configured.")

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{TRIPO_API_URL}/task/{task_id}",
                headers=headers,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        detail = error.response.text[:500] or "Tripo rejected the status request."
        raise HTTPException(status_code=502, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Could not reach Tripo AI.") from error

    try:
        result = response.json().get("data", {})
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=502, detail="Tripo returned an invalid JSON status response.") from error
    output = result.get("output") or {}
    model_url = output.get("model") or output.get("pbr_model")
    return {
        "task_id": task_id,
        "status": result.get("status", "unknown"),
        "model_url": model_url,
        "provider": "Tripo AI",
    }


@app.post("/generate/meshy")
async def generate_with_meshy(request: GenerateRequest):
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")

    api_key = configured_api_key("MESHY_API_KEY", "your_meshy_api_key_here")
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "mode": "preview",
        "prompt": prompt,
        "art_style": "realistic",
        "should_texture": True,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{MESHY_API_URL}/text-to-3d",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        detail = error.response.text[:500] or "Meshy rejected the request."
        raise HTTPException(status_code=502, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Could not reach Meshy AI.") from error

    try:
        result = response.json()
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=502, detail="Meshy returned invalid JSON.") from error
    task_id = result.get("result")
    if not task_id:
        raise HTTPException(status_code=502, detail="Meshy returned no task ID.")
    return {"task_id": task_id, "provider": "Meshy AI", "prompt": prompt}


@app.get("/generate/meshy/status/{task_id}")
async def get_meshy_task(task_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", task_id):
        raise HTTPException(status_code=422, detail="Invalid Meshy task ID.")

    api_key = configured_api_key("MESHY_API_KEY", "your_meshy_api_key_here")
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{MESHY_API_URL}/text-to-3d/{task_id}",
                headers=headers,
            )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        detail = error.response.text[:500] or "Meshy rejected the status request."
        raise HTTPException(status_code=502, detail=detail) from error
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Could not reach Meshy AI.") from error

    try:
        result = response.json()
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=502, detail="Meshy returned invalid status JSON.") from error
    model_urls = result.get("model_urls") or {}
    return {
        "task_id": task_id,
        "status": result.get("status", "unknown").lower(),
        "model_url": model_urls.get("glb") or model_urls.get("obj"),
        "provider": "Meshy AI",
    }


if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
