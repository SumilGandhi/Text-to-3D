import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import './styles.css';

async function readJsonResponse(response, fallbackMessage) {
  const body = await response.text();
  if (!body.trim()) {
    throw new Error(`${fallbackMessage} (empty response, HTTP ${response.status})`);
  }

  try {
    return JSON.parse(body);
  } catch {
    throw new Error(`${fallbackMessage} (HTTP ${response.status})`);
  }
}

function ScenePreview({ sceneSpec }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const mountNode = mountRef.current;
    if (!mountNode) {
      return undefined;
    }

    mountNode.innerHTML = '';

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(mountNode.clientWidth, mountNode.clientHeight);
    mountNode.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);

    const camera = new THREE.PerspectiveCamera(
      45,
      mountNode.clientWidth / mountNode.clientHeight,
      0.1,
      100,
    );
    camera.position.set(3.5, 2.5, 4.5);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    scene.add(new THREE.AmbientLight(0xffffff, 1.2));

    const directionalLight = new THREE.DirectionalLight(0xffffff, 2.2);
    directionalLight.position.set(4, 6, 5);
    scene.add(directionalLight);

    const grid = new THREE.GridHelper(10, 10, 0x334155, 0x1e293b);
    grid.position.y = -1.8;
    scene.add(grid);

    const object = new THREE.Group();
    const geometries = [];
    const materials = [];
    const part = (geometry, color, position = [0, 0, 0], scale = [1, 1, 1]) => {
      const material = new THREE.MeshStandardMaterial({ color, metalness: 0.2, roughness: 0.4 });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(...position);
      mesh.scale.set(...scale);
      object.add(mesh);
      geometries.push(geometry);
      materials.push(material);
      return mesh;
    };
    if (sceneSpec.model_url) {
      const loader = new GLTFLoader();
      loader.load(
        sceneSpec.model_url,
        (gltf) => {
          object.add(gltf.scene);
          gltf.scene.scale.setScalar(sceneSpec.scale || 1);
        },
        undefined,
        (error) => console.error('Could not load Tripo model.', error),
      );
    }

    if (!sceneSpec.model_url) {
      const color = sceneSpec.color;
      const dark = '#111827';
      const glass = '#93c5fd';
      if (sceneSpec.object_type === 'car') {
      part(new THREE.BoxGeometry(2.8, 0.6, 1.3), color, [0, 0, 0]);
      part(new THREE.BoxGeometry(1.4, 0.55, 1.1), color, [0.2, 0.52, 0]);
      [-0.95, 0.95].forEach((x) => [-0.72, 0.72].forEach((z) => {
        part(new THREE.CylinderGeometry(0.3, 0.3, 0.18, 24), dark, [x, -0.38, z], [1, 1, 1]);
        object.children.at(-1).rotation.x = Math.PI / 2;
      }));
      part(new THREE.BoxGeometry(0.7, 0.28, 0.04), glass, [0.2, 0.58, 0.56]);
    } else if (sceneSpec.object_type === 'truck') {
      part(new THREE.BoxGeometry(1.9, 0.75, 1.25), color, [-0.55, 0, 0]);
      part(new THREE.BoxGeometry(1.1, 1.05, 1.2), color, [1, 0.15, 0]);
      part(new THREE.BoxGeometry(0.72, 0.4, 0.04), glass, [1, 0.42, 0.61]);
      [-1.05, 0.9].forEach((x) => [-0.68, 0.68].forEach((z) => {
        part(new THREE.CylinderGeometry(0.3, 0.3, 0.2, 24), dark, [x, -0.48, z]);
        object.children.at(-1).rotation.x = Math.PI / 2;
      }));
    } else if (sceneSpec.object_type === 'bus') {
      part(new THREE.BoxGeometry(3, 1.25, 1.25), color, [0, 0, 0]);
      part(new THREE.BoxGeometry(2.4, 0.45, 0.04), glass, [0, 0.45, 0.63]);
      [-1.05, 1.05].forEach((x) => [-0.68, 0.68].forEach((z) => {
        part(new THREE.CylinderGeometry(0.28, 0.28, 0.18, 20), dark, [x, -0.72, z]);
        object.children.at(-1).rotation.x = Math.PI / 2;
      }));
    } else if (sceneSpec.object_type === 'motorcycle') {
      [-0.75, 0.75].forEach((x) => {
        part(new THREE.TorusGeometry(0.38, 0.12, 12, 24), dark, [x, -0.55, 0]);
        object.children.at(-1).rotation.y = Math.PI / 2;
      });
      part(new THREE.BoxGeometry(1.1, 0.28, 0.35), color, [0, -0.15, 0]);
      part(new THREE.CylinderGeometry(0.06, 0.06, 1.1, 12), dark, [0.55, 0.35, 0]);
    } else if (sceneSpec.object_type === 'airplane') {
      part(new THREE.CylinderGeometry(0.28, 0.28, 2.8, 20), color, [0, 0, 0], [1, 1, 1]);
      object.children.at(-1).rotation.z = Math.PI / 2;
      part(new THREE.ConeGeometry(0.42, 0.9, 20), color, [1.8, 0, 0]);
      object.children.at(-1).rotation.z = -Math.PI / 2;
      part(new THREE.BoxGeometry(0.8, 0.08, 3.2), color, [0, 0, 0]);
      part(new THREE.BoxGeometry(0.55, 0.08, 1.1), color, [-0.9, 0.35, 0]);
    } else if (sceneSpec.object_type === 'boat') {
      part(new THREE.ConeGeometry(0.9, 2.8, 4), color, [0, -0.45, 0], [1, 1, 0.7]);
      object.children.at(-1).rotation.z = Math.PI / 2;
      part(new THREE.BoxGeometry(0.9, 0.7, 0.8), '#f8fafc', [0, 0.35, 0]);
      part(new THREE.CylinderGeometry(0.05, 0.05, 1.5, 12), dark, [0, 1, 0]);
    } else if (sceneSpec.object_type === 'chair') {
      part(new THREE.BoxGeometry(1.2, 0.18, 1.1), color, [0, 0.25, 0]);
      part(new THREE.BoxGeometry(1.2, 1.3, 0.18), color, [0, 0.9, -0.46]);
      [-0.42, 0.42].forEach((x) => [-0.38, 0.38].forEach((z) => {
        part(new THREE.CylinderGeometry(0.08, 0.08, 1.2, 12), dark, [x, -0.35, z]);
      }));
    } else if (sceneSpec.object_type === 'table') {
      part(new THREE.BoxGeometry(2.4, 0.18, 1.4), color, [0, 0.65, 0]);
      [-0.9, 0.9].forEach((x) => [-0.45, 0.45].forEach((z) => {
        part(new THREE.CylinderGeometry(0.1, 0.1, 1.3, 12), dark, [x, 0, z]);
      }));
    } else if (sceneSpec.object_type === 'lamp') {
      part(new THREE.CylinderGeometry(0.08, 0.08, 1.8, 16), dark, [0, -0.6, 0]);
      part(new THREE.ConeGeometry(0.6, 0.65, 24), color, [0, 0.35, 0]);
      part(new THREE.SphereGeometry(0.18, 16, 12), '#fde68a', [0, 0.1, 0]);
    } else if (sceneSpec.object_type === 'flower') {
      part(new THREE.CylinderGeometry(0.08, 0.08, 1.3, 12), '#16a34a', [0, -0.7, 0]);
      for (let index = 0; index < 6; index += 1) {
        const angle = (index / 6) * Math.PI * 2;
        part(new THREE.SphereGeometry(0.35, 16, 12), color, [Math.cos(angle) * 0.32, 0.15, Math.sin(angle) * 0.32]);
      }
      part(new THREE.SphereGeometry(0.2, 16, 12), '#facc15', [0, 0.15, 0]);
    } else if (sceneSpec.object_type === 'tree') {
      part(new THREE.CylinderGeometry(0.28, 0.38, 1.8, 16), '#8b5a2b', [0, -0.5, 0]);
      part(new THREE.SphereGeometry(1.05, 24, 16), color === '#f15bb5' ? '#22c55e' : color, [0, 0.8, 0]);
    } else if (sceneSpec.object_type === 'rocket') {
      part(new THREE.CylinderGeometry(0.55, 0.55, 1.8, 24), color, [0, 0, 0]);
      part(new THREE.ConeGeometry(0.55, 0.9, 24), '#f8fafc', [0, 1.35, 0]);
      part(new THREE.ConeGeometry(0.35, 0.7, 4), '#f97316', [0, -1.2, 0]);
    } else if (sceneSpec.object_type === 'house') {
      part(new THREE.BoxGeometry(1.8, 1.5, 1.6), color, [0, -0.2, 0]);
      part(new THREE.ConeGeometry(1.35, 0.9, 4), '#b91c1c', [0, 1, 0], [1, 1, 0.85]);
      part(new THREE.BoxGeometry(0.4, 0.75, 0.05), '#78350f', [0, -0.55, 0.83]);
    } else if (sceneSpec.object_type === 'robot') {
      const robotMetal = '#475569';
      const robotJoint = '#111827';
      part(new THREE.BoxGeometry(1.2, 1.3, 0.8), color, [0, 0.1, 0]);
      part(new THREE.BoxGeometry(0.9, 0.7, 0.7), robotMetal, [0, 1.2, 0]);
      part(new THREE.BoxGeometry(0.16, 0.16, 0.16), robotJoint, [-0.7, 0.75, 0]);
      part(new THREE.BoxGeometry(0.16, 0.16, 0.16), robotJoint, [0.7, 0.75, 0]);
      [-1, 1].forEach((side) => {
        part(new THREE.BoxGeometry(0.28, 0.55, 0.3), robotMetal, [side * 0.88, 0.38, 0]);
        part(new THREE.SphereGeometry(0.18, 16, 12), robotJoint, [side * 0.88, 0.02, 0]);
        part(new THREE.BoxGeometry(0.28, 0.55, 0.3), robotMetal, [side * 0.88, -0.35, 0]);
        part(new THREE.BoxGeometry(0.34, 0.2, 0.34), color, [side * 0.88, -0.7, 0]);
        part(new THREE.BoxGeometry(0.4, 0.9, 0.38), robotMetal, [side * 0.36, -0.95, 0]);
        part(new THREE.SphereGeometry(0.18, 16, 12), robotJoint, [side * 0.36, -1.48, 0]);
        part(new THREE.BoxGeometry(0.4, 0.9, 0.38), robotMetal, [side * 0.36, -1.98, 0]);
        part(new THREE.BoxGeometry(0.55, 0.22, 0.7), color, [side * 0.36, -2.52, -0.12]);
      });
      part(new THREE.SphereGeometry(0.1, 16, 12), '#22d3ee', [-0.22, 1.24, 0.37]);
      part(new THREE.SphereGeometry(0.1, 16, 12), '#22d3ee', [0.22, 1.24, 0.37]);
      } else {
        const geometryMap = {
          box: () => new THREE.BoxGeometry(1.6, 1.1, 1.1),
          sphere: () => new THREE.SphereGeometry(0.9, 48, 32),
          cylinder: () => new THREE.CylinderGeometry(0.8, 0.8, 1.8, 32),
          torus: () => new THREE.TorusGeometry(0.8, 0.28, 20, 80),
          cone: () => new THREE.ConeGeometry(0.95, 1.8, 32),
        };
        part(geometryMap[sceneSpec.shape](), color);
      }
    }
    object.scale.setScalar(sceneSpec.scale);
    scene.add(object);

    let frameId;

    const animate = () => {
      frameId = window.requestAnimationFrame(animate);
      object.rotation.y += 0.01;
      object.rotation.x += 0.004;
      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      const width = mountNode.clientWidth;
      const height = mountNode.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.cancelAnimationFrame(frameId);
      controls.dispose();
      geometries.forEach((geometry) => geometry.dispose());
      materials.forEach((material) => material.dispose());
      renderer.dispose();
      mountNode.innerHTML = '';
    };
  }, [sceneSpec]);

  return <div className="viewer-canvas" ref={mountRef} />;
}

function App() {
  const [prompt, setPrompt] = useState('A low-poly red sports car');
  const [provider, setProvider] = useState('local');
  const [enhancePrompt, setEnhancePrompt] = useState(false);
  const [status, setStatus] = useState('Describe an object, then click Generate.');
  const [sceneSpec, setSceneSpec] = useState({
    shape: 'box',
    color: '#e63946',
    scale: 1,
    title: 'Generated box',
    description: 'Your free local 3D preview will appear here.',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [hasGeneratedModel, setHasGeneratedModel] = useState(false);
  const hasExportableModel = Boolean(sceneSpec.model_url);
  const [blenderStatus, setBlenderStatus] = useState('');

  const handleGenerate = async () => {
    const trimmedPrompt = prompt.trim();

    if (!trimmedPrompt) {
      setStatus('Please enter a description.');
      return;
    }

    setIsLoading(true);
    setStatus('Generating 3D scene...');

    try {
      const startEndpoint = provider === 'tripo'
        ? '/generate/tripo'
        : provider === 'meshy'
          ? '/generate/meshy'
          : '/generate';
      const statusEndpoint = provider === 'tripo' ? 'tripo' : 'meshy';
      const providerName = provider === 'tripo' ? 'Tripo AI' : 'Meshy AI';
      const response = await fetch(startEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: trimmedPrompt,
          enhance_prompt: provider === 'local' && enhancePrompt,
        }),
      });

      const data = await readJsonResponse(response, 'The server returned an invalid response.');
      if (!response.ok) {
        throw new Error(data.detail || 'Generation failed.');
      }
      if (provider === 'local') {
        setSceneSpec(data.scene);
        setHasGeneratedModel(true);
        setStatus(data.generated_prompt
          ? `Generated locally with OpenAI enhancement: ${data.generated_prompt}`
          : `Generated locally from: ${data.prompt}`);
      } else {
        let task = data;
        setStatus(`${providerName} is generating the model...`);
        for (let attempt = 0; attempt < 60; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, 3000));
          const taskResponse = await fetch(`/generate/${statusEndpoint}/status/${task.task_id}`);
          task = await readJsonResponse(taskResponse, `${providerName} status check returned an invalid response.`);
          if (!taskResponse.ok) {
            throw new Error(task.detail || `${providerName} generation failed.`);
          }
          if (['success', 'succeeded'].includes(task.status)) {
            setSceneSpec({
              model_url: task.model_url,
              scale: 1,
              title: `Generated ${providerName} model`,
              description: `Generated by ${providerName}.`,
            });
            setHasGeneratedModel(true);
            setStatus(`Generated by ${providerName}.`);
            break;
          }
          if (['failed', 'cancelled', 'banned', 'error'].includes(task.status)) {
            throw new Error(`${providerName} generation ${task.status}.`);
          }
          setStatus(`${providerName} status: ${task.status}...`);
        }
        if (!['success', 'succeeded'].includes(task.status)) {
          throw new Error(`${providerName} generation timed out.`);
        }
      }
    } catch (error) {
      console.error(error);
      setStatus(error.message || 'Could not generate the model.');
    } finally {
      setIsLoading(false);
    }
  };

  const sendToBlender = async () => {
    setBlenderStatus('Sending object to Blender...');
    try {
      const response = await fetch('http://127.0.0.1:8765/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...sceneSpec, prompt }),
      });
      const data = await readJsonResponse(response, 'Blender bridge returned an invalid response.');
      if (!response.ok) {
        throw new Error(data.detail || 'Blender bridge rejected the object.');
      }
      setBlenderStatus(data.message || 'Object queued in Blender. It should appear shortly.');
    } catch (error) {
      console.error(error);
      setBlenderStatus('Blender is not connected. Run the bridge add-on in Blender first.');
    }
  };

  return (
    <main className="app-shell">
      <section className="panel input-panel">
        <div className="eyebrow">Text to 3D</div>
        <h1>Generate a 3D object from text</h1>
        <p className="lede">
          Enter a prompt, click Generate, and a free local 3D preview will be created instantly.
        </p>

        <label className="field-label" htmlFor="prompt">Prompt</label>
        <label className="field-label" htmlFor="provider">Generator</label>
        <select id="provider" value={provider} onChange={(event) => setProvider(event.target.value)}>
          <option value="local">Local preview (default)</option>
          <option value="tripo">Tripo AI</option>
          <option value="meshy">Meshy AI</option>
        </select>
        {provider === 'local' && (
          <label className="enhance-toggle">
            <input
              type="checkbox"
              checked={enhancePrompt}
              onChange={(event) => setEnhancePrompt(event.target.checked)}
            />
            Enhance prompt with OpenAI
          </label>
        )}
        <textarea
          id="prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Example: A low-poly red sports car"
        />

        <button className="generate-button" onClick={handleGenerate} disabled={isLoading}>
          {isLoading ? 'Generating...' : 'Generate 3D Model'}
        </button>

        <div className="status-card">{status}</div>

        {hasGeneratedModel && (
          <div className="blender-workflow">
            <div className="eyebrow">Blender workflow</div>
            <h3>Continue this object in Blender</h3>
            {hasExportableModel ? (
              <>
                <p>Download the generated GLB, then open it in Blender.</p>
                <a
                  className="export-button"
                  href={sceneSpec.model_url}
                  target="_blank"
                  rel="noreferrer"
                  download
                >
                  Download GLB model
                </a>
              </>
            ) : (
              <p>
                This Local preview is procedural. Recreate the displayed shape in Blender
                using the object type and prompt below, then add detail with Blender tools.
              </p>
            )}
            <ol>
              <li>Open Blender.</li>
              {hasExportableModel && <li>Choose File, Import, glTF 2.0 (.glb/.gltf).</li>}
              {hasExportableModel && <li>Select the downloaded GLB file.</li>}
              {!hasExportableModel && <li>Add the matching primitive from the Add, Mesh menu.</li>}
              {!hasExportableModel && <li>Use the generated prompt as your modeling reference.</li>}
              <li>Edit, rig, light, or export the model.</li>
            </ol>
            <button className="export-button blender-button" onClick={sendToBlender}>
              Send to Blender
            </button>
            {blenderStatus && <p className="blender-status">{blenderStatus}</p>}
          </div>
        )}

        <div className="scene-meta">
          <div>
            <span>Provider</span>
            <strong>{provider === 'tripo' ? 'Tripo AI' : provider === 'meshy' ? 'Meshy AI' : 'Local'}</strong>
          </div>
          <div>
            <span>Format</span>
            <strong>Three.js</strong>
          </div>
          <div>
            <span>Status</span>
            <strong>{isLoading ? 'Generating' : 'Ready'}</strong>
          </div>
        </div>
      </section>

      <section className="panel viewer-panel">
        <div className="viewer-header">
          <div>
            <div className="eyebrow">3D Preview</div>
            <h2>{sceneSpec.title}</h2>
          </div>
          <p>{sceneSpec.description}</p>
        </div>

        <ScenePreview sceneSpec={sceneSpec} />
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);