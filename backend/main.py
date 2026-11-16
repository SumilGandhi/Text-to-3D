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
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DATASET_URL = os.getenv("DATASET_URL", "").strip()
LOCAL_AI_URL = os.getenv("LOCAL_AI_URL", "").rstrip("/")
LOCAL_AI_SECRET = os.getenv("LOCAL_AI_SECRET", "")

GENERATED_DIR = Path(__file__).resolve().parent / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

generation_jobs = {}
class GenerateRequest(BaseModel):
    prompt: str
    enhance_prompt: bool = False
class LocalGenerateRequest(BaseModel):
    prompt: str    


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

async def submit_local_generation(prompt: str) -> str:
    if not LOCAL_AI_URL or not LOCAL_AI_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Local AI server is not configured."
        )

    headers = {"X-API-Secret": LOCAL_AI_SECRET}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{LOCAL_AI_URL}/generate",
                headers=headers,
                json={"prompt": prompt},
            )
            response.raise_for_status()
            return response.json()["job_id"]

    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail="Could not contact the local AI server."
        ) from error


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

    generated_prompt = (
        await enhance_prompt_with_openai(prompt)
        if request.enhance_prompt
        else prompt
    )

    job_id = await submit_local_generation(generated_prompt)

    generation_jobs[job_id] = {
        "prompt": prompt,
        "generated_prompt": generated_prompt,
        "status": "queued",
        "scene": None,
    }

    return {
        "message": "Generation job submitted",
        "job_id": job_id,
        "status": "queued",
    }



@app.get("/generate/{job_id}")
async def get_generation_status(job_id: str):
    job = generation_jobs.get(job_id)

    # Recover an already-generated model if the job is no longer in memory.
    if job is None:
        model_filename = f"{job_id}.glb"
        model_path = GENERATED_DIR / model_filename

        if not model_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Generation job not found."
            )

        scene = build_scene_spec("A low-poly red sports car").model_dump()
        scene["model_url"] = f"/generated/{model_filename}"

        return {
            "status": "completed",
            "scene": scene,
        }

    if job["status"] == "completed":
        return {
            "status": "completed",
            "scene": job["scene"],
        }

    headers = {"X-API-Secret": LOCAL_AI_SECRET}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{LOCAL_AI_URL}/status/{job_id}",
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()

            if result["status"] == "failed":
                job["status"] = "failed"
                return {
                    "status": "failed",
                    "error": result.get("error", "Generation failed."),
                }

            if result["status"] != "completed":
                job["status"] = result["status"]
                return {"status": result["status"]}

            file_response = await client.get(
                f"{LOCAL_AI_URL}/result/{job_id}",
                headers=headers,
            )
            file_response.raise_for_status()

        model_filename = f"{job_id}.glb"
        model_path = GENERATED_DIR / model_filename
        model_path.write_bytes(file_response.content)

        scene = build_scene_spec(job["generated_prompt"]).model_dump()
        scene["model_url"] = f"/generated/{model_filename}"

        job["scene"] = scene
        job["status"] = "completed"

        return {
            "status": "completed",
            "scene": scene,
        }

    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve the generated 3D model."
        ) from error




@app.get("/dataset")
async def get_dataset():
    if not DATASET_URL:
        raise HTTPException(
            status_code=404,
            detail="DATASET_URL is not configured. Add it to the project .env file.",
        )
    return {"url": DATASET_URL}


app.mount(
    "/generated",
    StaticFiles(directory=GENERATED_DIR),
    name="generated",
)

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

