
import os
import gc
import torch
import trimesh

from pathlib import Path
from shap_e.diffusion.sample import sample_latents
from shap_e.diffusion.gaussian_diffusion import diffusion_from_config
from shap_e.models.download import load_model, load_config
from shap_e.util.notebooks import decode_latent_mesh


# Project paths
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# GPU configuration
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Model settings
BATCH_SIZE = 1
GUIDANCE_SCALE = 15.0
KARRAS_STEPS = 16

# Load models once
print("Loading Shap-E models...")
print(f"Device: {DEVICE}")

TRANSMITTER = load_model("transmitter", device=DEVICE)
MODEL = load_model("text300M", device=DEVICE)
DIFFUSION = diffusion_from_config(load_config("diffusion"))

print("Shap-E models loaded successfully!")


def generate_3d(prompt: str) -> str:
    """
    Generate a 3D model from a text prompt.
    Returns the generated GLB file path.
    """

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    print(f"Generating: {prompt}")

    latents = sample_latents(
        batch_size=BATCH_SIZE,
        model=MODEL,
        diffusion=DIFFUSION,
        guidance_scale=GUIDANCE_SCALE,
        model_kwargs={"texts": [prompt]},
        progress=True,
        clip_denoised=True,
        use_fp16=True,
        use_karras=True,
        karras_steps=KARRAS_STEPS,
        sigma_min=1e-3,
        sigma_max=160,
        s_churn=0,
    )

    print("Converting generated model to mesh...")

    mesh_data = decode_latent_mesh(TRANSMITTER, latents[0])
    mesh = mesh_data.tri_mesh()

    obj_path = OUTPUT_DIR / "generated_model.obj"
    glb_path = OUTPUT_DIR / "generated_model.glb"

    with open(obj_path, "w", encoding="utf-8") as file:
        mesh.write_obj(file)

    print("Converting OBJ to GLB...")

    loaded_mesh = trimesh.load(obj_path, force="mesh")
    loaded_mesh.export(glb_path, file_type="glb")

    del latents
    del mesh_data
    del mesh
    del loaded_mesh

    gc.collect()

    if DEVICE.type == "cuda":
        torch.cuda.empty_cache()

    print(f"Model saved: {glb_path}")

    return str(glb_path)


if __name__ == "__main__":
    prompt = input("Enter your 3D model description: ").strip()

    try:
        result = generate_3d(prompt)
        print(f"\nSUCCESS! Generated model: {result}")
    except Exception as error:
        print(f"\nGENERATION FAILED: {error}")
        raise
