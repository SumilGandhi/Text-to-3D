bl_info = {
    "name": "Text to 3D Local Bridge",
    "author": "Text-to-3D",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Text to 3D",
    "category": "3D View",
}

import bpy
import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mathutils import Matrix


BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8765
REQUEST_QUEUE = queue.Queue()
SERVER = None
SERVER_THREAD = None
LAST_ERROR = ""
LAST_MESSAGE = "Bridge started. Waiting for an object."


def material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    return mat


def color_from_hex(value):
    value = (value or "#e63946").lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    try:
        return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))
    except ValueError:
        return (0.9, 0.22, 0.27)


def add_cube(name, location, scale, mat):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    vertices = [
        (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7),
    ]
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def remove_previous_generated_objects():
    for existing in list(bpy.data.objects):
        if existing.name.startswith("TextTo3D_"):
            bpy.data.objects.remove(existing, do_unlink=True)


def add_car(name, mat, truck=False):
    # Vehicle coordinates: X is length, Y is width, and Z is height.
    body_length = 3.8 if truck else 3.2
    body_width = 1.7
    body_height = 0.62
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    half_length = body_length / 2
    half_width = body_width / 2
    bottom = 0.25
    top = 0.85
    vertices = [
        (-half_length, -half_width, bottom),
        (half_length, -half_width, bottom),
        (half_length, half_width, bottom),
        (-half_length, half_width, bottom),
        (-half_length * 0.92, -half_width, top),
        (half_length * 0.92, -half_width, top),
        (half_length * 0.92, half_width, top),
        (-half_length * 0.92, half_width, top),
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7),
    ]
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    body = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(body)
    bevel = body.modifiers.new("Rounded body", "BEVEL")
    bevel.width = 0.12
    bevel.segments = 3
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    window_mat = material("TextTo3D Windows", (0.03, 0.12, 0.2))
    cabin_x = 0.75 if truck else 0.25
    cabin_length = 1.35 if truck else 1.55
    cabin = add_cube(
        f"{name}_Cabin",
        (cabin_x, 0, 1.12),
        (cabin_length / 2, 0.68, 0.35),
        window_mat,
    )
    cabin_bevel = cabin.modifiers.new("Rounded cabin", "BEVEL")
    cabin_bevel.width = 0.14
    cabin_bevel.segments = 2
    wheel_mat = material("TextTo3D Tires", (0.03, 0.03, 0.03))
    wheel_x_positions = (-1.25, 1.25) if truck else (-1.05, 1.05)
    for index, x in enumerate(wheel_x_positions):
        for y in (-0.72, 0.72):
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=24,
                radius=0.36,
                depth=0.22,
                location=(x, y, 0.38),
                rotation=(1.5708, 0, 0),
            )
            wheel = bpy.context.object
            wheel.name = f"{name}_Wheel_{index}_{'L' if y < 0 else 'R'}"
            wheel.data.materials.append(wheel_mat)
    light_mat = material("TextTo3D Lights", (1.0, 0.8, 0.1))
    for index, x in enumerate((-body_length / 2, body_length / 2)):
        light = add_cube(
            f"{name}_Light_{index}",
            (x, 0, 0.62),
            (0.08, 0.35, 0.1),
            light_mat,
        )
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    return body


def add_motorcycle(name, mat):
    tire_mat = material("TextTo3D Tires", (0.03, 0.03, 0.03))
    metal_mat = material("TextTo3D Metal", (0.12, 0.14, 0.16))
    for index, x in enumerate((-1.15, 1.15)):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.42,
            minor_radius=0.12,
            major_segments=24,
            location=(x, 0, 0.48),
            rotation=(1.5708, 0, 0),
        )
        wheel = bpy.context.object
        wheel.name = f"{name}_Wheel_{index}"
        wheel.data.materials.append(tire_mat)
    body = add_cube(f"{name}_Frame", (0, 0, 0.82), (0.95, 0.22, 0.18), metal_mat)
    seat = add_cube(f"{name}_Seat", (0.35, 0, 1.12), (0.5, 0.3, 0.12), mat)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=20, radius=0.06, depth=0.85, location=(0.85, 0, 1.22),
        rotation=(0, 0.35, 0),
    )
    fork = bpy.context.object
    fork.name = f"{name}_Fork"
    fork.data.materials.append(metal_mat)
    handle = add_cube(f"{name}_Handle", (0.72, 0, 1.58), (0.3, 0.05, 0.05), metal_mat)
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    return body


def add_robot(name, mat):
    metal = material("TextTo3D Robot Metal", (0.18, 0.2, 0.24))
    body = add_cube(name, (0, 0, 1.5), (0.65, 0.45, 0.75), mat)
    head = add_cube(f"{name}_Head", (0, 0, 2.65), (0.48, 0.4, 0.4), metal)
    joint_mat = material("TextTo3D Robot Joints", (0.05, 0.06, 0.08))
    for side in (-1, 1):
        shoulder_x = side * 0.9
        add_cube(
            f"{name}_Shoulder_{side}",
            (shoulder_x, 0, 2.0),
            (0.22, 0.24, 0.22),
            joint_mat,
        )
        add_cube(
            f"{name}_UpperArm_{side}",
            (shoulder_x, 0, 1.62),
            (0.2, 0.2, 0.32),
            metal,
        )
        add_cube(
            f"{name}_Elbow_{side}",
            (shoulder_x, 0, 1.25),
            (0.22, 0.22, 0.18),
            joint_mat,
        )
        add_cube(
            f"{name}_Forearm_{side}",
            (shoulder_x, 0, 0.9),
            (0.2, 0.2, 0.3),
            metal,
        )
        add_cube(
            f"{name}_Hand_{side}",
            (shoulder_x, -0.02, 0.55),
            (0.24, 0.24, 0.18),
            mat,
        )
        hip_x = side * 0.35
        add_cube(f"{name}_Hip_{side}", (hip_x, 0, 0.72), (0.25, 0.3, 0.2), joint_mat)
        add_cube(f"{name}_UpperLeg_{side}", (hip_x, 0, 0.2), (0.22, 0.28, 0.38), metal)
        add_cube(f"{name}_Knee_{side}", (hip_x, -0.02, -0.25), (0.24, 0.3, 0.18), joint_mat)
        add_cube(f"{name}_LowerLeg_{side}", (hip_x, 0, -0.68), (0.22, 0.28, 0.38), metal)
        add_cube(f"{name}_Foot_{side}", (hip_x + 0.12, -0.16, -1.15), (0.34, 0.42, 0.18), mat)
    eye_mat = material("TextTo3D Robot Eyes", (0.1, 0.8, 1.0))
    add_cube(f"{name}_Eye", (0, -0.42, 2.68), (0.22, 0.04, 0.08), eye_mat)
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    return body


def add_weapon(name, mat, sniper=False):
    metal = material("TextTo3D Weapon Metal", (0.08, 0.09, 0.1))
    grip = add_cube(f"{name}_Grip", (-0.45, 0, 0.15), (0.18, 0.22, 0.55), mat)
    body = add_cube(name, (0.25, 0, 0.65), (0.8 if sniper else 0.55, 0.25, 0.2), metal)
    barrel_length = 2.8 if sniper else 1.1
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=20, radius=0.12, depth=barrel_length,
        location=(1.15 if sniper else 1.0, 0, 0.7),
        rotation=(0, 1.5708, 0),
    )
    barrel = bpy.context.object
    barrel.name = f"{name}_Barrel"
    barrel.data.materials.append(metal)
    if sniper:
        add_cube(f"{name}_Stock", (-0.95, 0, 0.7), (0.5, 0.2, 0.16), mat)
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=20, radius=0.16, depth=0.8, location=(0.1, 0, 1.08),
            rotation=(0, 1.5708, 0),
        )
        scope = bpy.context.object
        scope.name = f"{name}_Scope"
        scope.data.materials.append(metal)
    bpy.context.view_layer.objects.active = body
    body.select_set(True)
    return body


def add_object(scene_data):
    remove_previous_generated_objects()
    object_type = scene_data.get("object_type", "sphere")
    color = material("TextTo3D Color", color_from_hex(scene_data.get("color")))
    name = f"TextTo3D_{object_type}"

    if object_type == "test_cube":
        obj = add_cube(name, (0, 0, 0), (1.2, 1.2, 1.2), color)
    elif object_type == "car":
        obj = add_car(name, color)
    elif object_type == "truck":
        obj = add_car(name, color, truck=True)
    elif object_type == "motorcycle":
        obj = add_motorcycle(name, color)
    elif object_type == "robot":
        obj = add_robot(name, color)
    elif object_type == "pistol":
        obj = add_weapon(name, color)
    elif object_type == "sniper":
        obj = add_weapon(name, color, sniper=True)
    elif object_type in {"bus", "house", "chair", "table"}:
        obj = add_cube(name, (0, 0, 0), (1.2, 0.7, 0.6), color)
    elif object_type == "tree":
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.35, depth=1.8, location=(0, 0, 0))
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(color)
    elif object_type in {"rocket", "cone", "airplane"}:
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.8, radius2=0, depth=1.8, location=(0, 0, 0))
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(color)
    elif object_type in {"cylinder", "lamp", "flower"}:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.8, depth=1.8, location=(0, 0, 0))
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(color)
    elif object_type in {"torus", "ring"}:
        bpy.ops.mesh.primitive_torus_add(major_radius=0.8, minor_radius=0.25, location=(0, 0, 0))
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(color)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=(0, 0, 0))
        obj = bpy.context.object
        obj.name = name
        obj.data.materials.append(color)

    try:
        requested_scale = float(scene_data.get("scale") or 1)
    except (TypeError, ValueError):
        requested_scale = 1
    visible_scale = max(0.5, min(requested_scale, 10))
    obj.scale = (visible_scale,) * 3
    obj.hide_viewport = False
    obj.hide_render = False
    for selected in bpy.context.selected_objects:
        selected.select_set(False)
    for generated in bpy.data.objects:
        if generated.name == name or generated.name.startswith(f"{name}_"):
            generated.select_set(True)
    obj["text_to_3d_prompt"] = scene_data.get("prompt", "")
    obj["text_to_3d_axis_convention"] = "X=length, Y=width, Z=height"
    bpy.context.view_layer.objects.active = obj
    for generated in bpy.data.objects:
        if generated.name == name or generated.name.startswith(f"{name}_"):
            generated.data.transform(
                Matrix.Diagonal((
                    generated.scale.x,
                    generated.scale.y,
                    generated.scale.z,
                    1,
                ))
            )
            generated.scale = (1, 1, 1)
            generated["text_to_3d_generated"] = True


def process_requests():
    global LAST_ERROR, LAST_MESSAGE
    try:
        while True:
            scene_data = REQUEST_QUEUE.get_nowait()
            try:
                add_object(scene_data)
            except Exception:
                REQUEST_QUEUE.put(scene_data)
                raise
            LAST_MESSAGE = f"Created {scene_data.get('object_type', 'object')} in Blender."
    except queue.Empty:
        pass
    except Exception as error:
        LAST_ERROR = str(error)
        print(f"Text to 3D bridge error: {error}")
    return 0.25


def process_pending_operator():
    process_requests()
    return {"FINISHED"}


class BridgeHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        global LAST_MESSAGE
        if self.path != "/generate":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length))
            REQUEST_QUEUE.put(payload)
            LAST_MESSAGE = "Object received. Waiting for Blender to process it."
            body = json.dumps({"ok": True, "message": "Object queued in Blender"}).encode()
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except (ValueError, TypeError):
            self.send_error(400, "Invalid JSON")

    def do_GET(self):
        if self.path != "/status":
            self.send_error(404)
            return
        body = json.dumps({
            "ok": True,
            "queue_size": REQUEST_QUEUE.qsize(),
            "last_message": LAST_MESSAGE,
            "last_error": LAST_ERROR,
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


def start_bridge():
    global SERVER, SERVER_THREAD, LAST_ERROR, LAST_MESSAGE
    if SERVER is not None:
        return
    try:
        SERVER = ThreadingHTTPServer((BRIDGE_HOST, BRIDGE_PORT), BridgeHandler)
        SERVER_THREAD = threading.Thread(target=SERVER.serve_forever, daemon=True)
        SERVER_THREAD.start()
        LAST_MESSAGE = f"Listening on http://{BRIDGE_HOST}:{BRIDGE_PORT}"
        print(f"Text to 3D Blender bridge listening on http://{BRIDGE_HOST}:{BRIDGE_PORT}")
    except OSError as error:
        SERVER = None
        SERVER_THREAD = None
        LAST_ERROR = f"Port {BRIDGE_PORT} is already in use. Stop the old bridge and run this script again."
        print(f"Text to 3D bridge could not start: {error}")

    if not bpy.app.timers.is_registered(process_requests):
        bpy.app.timers.register(process_requests, first_interval=0.25, persistent=True)


def stop_bridge():
    global SERVER, SERVER_THREAD
    if SERVER is not None:
        SERVER.shutdown()
        SERVER.server_close()
        SERVER = None
        SERVER_THREAD = None


class TEXT3D_PT_bridge(bpy.types.Panel):
    bl_label = "Text to 3D Bridge"
    bl_idname = "TEXT3D_PT_bridge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Text to 3D"

    def draw(self, _context):
        global LAST_ERROR, LAST_MESSAGE
        self.layout.label(text=f"Listening on port {BRIDGE_PORT}")
        self.layout.label(text=LAST_MESSAGE)
        if LAST_ERROR:
            self.layout.label(text=f"Error: {LAST_ERROR}", icon="ERROR")
        self.layout.operator("text3d.create_test_object", text="Create Test Object")
        self.layout.operator("text3d.process_pending", text="Process Pending")
        self.layout.operator("text3d.frame_selected", text="Frame Selected Object")


class TEXT3D_OT_process_pending(bpy.types.Operator):
    bl_idname = "text3d.process_pending"
    bl_label = "Process Pending Text to 3D Object"

    def execute(self, _context):
        return process_pending_operator()


class TEXT3D_OT_create_test_object(bpy.types.Operator):
    bl_idname = "text3d.create_test_object"
    bl_label = "Create Test Object"

    def execute(self, _context):
        global LAST_ERROR, LAST_MESSAGE
        try:
            add_object({
                "object_type": "test_cube",
                "color": "#22aa66",
                "scale": 1,
                "prompt": "Bridge test object",
            })
            LAST_ERROR = ""
            LAST_MESSAGE = "Created TextTo3D_test_cube. It is selected; move over the viewport and press Numpad ."
        except Exception as error:
            LAST_ERROR = str(error)
            self.report({"ERROR"}, LAST_ERROR)
        return {"FINISHED"}


class TEXT3D_OT_frame_selected(bpy.types.Operator):
    bl_idname = "text3d.frame_selected"
    bl_label = "Frame Selected Text to 3D Object"

    def execute(self, _context):
        selected = bpy.context.selected_objects
        if not selected:
            self.report({"WARNING"}, "No Text to 3D object is selected.")
            return {"CANCELLED"}
        bpy.ops.view3d.view_selected(use_all_regions=False)
        return {"FINISHED"}


classes = (
    TEXT3D_PT_bridge,
    TEXT3D_OT_process_pending,
    TEXT3D_OT_create_test_object,
    TEXT3D_OT_frame_selected,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    start_bridge()


def unregister():
    stop_bridge()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
