import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import './styles.css';

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
      part(new THREE.BoxGeometry(1.2, 1.3, 0.8), color, [0, -0.2, 0]);
      part(new THREE.BoxGeometry(0.9, 0.7, 0.7), color, [0, 0.9, 0]);
      part(new THREE.SphereGeometry(0.1, 16, 12), '#22d3ee', [-0.22, 0.95, 0.37]);
      part(new THREE.SphereGeometry(0.1, 16, 12), '#22d3ee', [0.22, 0.95, 0.37]);
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
  const [status, setStatus] = useState('Describe an object, then click Generate.');
  const [sceneSpec, setSceneSpec] = useState({
    shape: 'box',
    color: '#e63946',
    scale: 1,
    title: 'Generated box',
    description: 'Your free local 3D preview will appear here.',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerate = async () => {
    const trimmedPrompt = prompt.trim();

    if (!trimmedPrompt) {
      setStatus('Please enter a description.');
      return;
    }

    setIsLoading(true);
    setStatus('Generating 3D scene...');

    try {
      const response = await fetch('/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: trimmedPrompt }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Generation failed.');
      }
      setSceneSpec(data.scene);
      setStatus(`Generated locally from: ${data.prompt}`);
    } catch (error) {
      console.error(error);
      setStatus(error.message || 'Could not generate the model.');
    } finally {
      setIsLoading(false);
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

        <div className="scene-meta">
          <div>
            <span>Provider</span>
            <strong>Local</strong>
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