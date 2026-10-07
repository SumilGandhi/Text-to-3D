from pathlib import Path
import re
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Text-to-3D Generator")
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

#hi
class GenerateRequest(BaseModel):
    prompt: str


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
    if any(word in normalized_prompt for word in ["car", "truck", "vehicle"]):
        shape, object_type = "box", "car"
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
        title=f"Generated {shape}",
        description=f"Free local preview mapped '{prompt}' to a {shape} scene object.",
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate")
def generate_model(request: GenerateRequest):
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")
    return {
        "message": "Generation completed",
        "prompt": prompt,
        "scene": build_scene_spec(prompt).model_dump(),
    }


if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
