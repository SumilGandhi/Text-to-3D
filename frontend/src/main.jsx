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

    const geometryMap = {
      box: () => new THREE.BoxGeometry(1.6, 1.1, 1.1),
      sphere: () => new THREE.SphereGeometry(0.9, 48, 32),
      cylinder: () => new THREE.CylinderGeometry(0.8, 0.8, 1.8, 32),
      torus: () => new THREE.TorusGeometry(0.8, 0.28, 20, 80),
      cone: () => new THREE.ConeGeometry(0.95, 1.8, 32),
    };

    const geometry = geometryMap[sceneSpec.shape]();
    const material = new THREE.MeshStandardMaterial({
      color: sceneSpec.color,
      metalness: 0.25,
      roughness: 0.35,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.scale.setScalar(sceneSpec.scale);
    scene.add(mesh);

    const grid = new THREE.GridHelper(10, 10, 0x334155, 0x1e293b);
    grid.position.y = -1.8;
    scene.add(grid);

    let frameId;

    const animate = () => {
      frameId = window.requestAnimationFrame(animate);
      mesh.rotation.y += 0.01;
      mesh.rotation.x += 0.004;
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
      geometry.dispose();
      material.dispose();
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
    description: 'Your 3D preview will appear here.',
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
      setSceneSpec(data.scene);
      setStatus(`Backend received: ${data.prompt}`);
    } catch (error) {
      console.error(error);
      setStatus('Could not connect to the backend.');
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
          Enter a prompt, click Generate, and the backend will return a 3D scene spec that is rendered on the right.
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
            <span>Shape</span>
            <strong>{sceneSpec.shape}</strong>
          </div>
          <div>
            <span>Color</span>
            <strong>{sceneSpec.color}</strong>
          </div>
          <div>
            <span>Scale</span>
            <strong>{sceneSpec.scale}</strong>
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