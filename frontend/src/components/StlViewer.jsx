import React, { useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Center, ContactShadows } from "@react-three/drei";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";
import * as THREE from "three";

// Model sub-component that loads the GLB geometry from the URL
function Model({ url, isLightMode }) {
  const [scene, setScene] = useState(null);

  useEffect(() => {
    if (!url) return;
    const loader = new GLTFLoader();
    
    // Load geometry
    loader.load(
      url,
      (gltf) => {
        gltf.scene.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = false; // Disable self-shadowing to completely eliminate shadow acne/stripes
            child.material = new THREE.MeshStandardMaterial({
              color: isLightMode ? "#3b82f6" : "#ffffff",      // Cool steel blue in light mode, white in dark mode
              roughness: isLightMode ? 0.3 : 0.4,
              metalness: isLightMode ? 0.6 : 0.1,
              side: THREE.DoubleSide
            });
            child.geometry.computeVertexNormals();
          }
        });
        setScene(gltf.scene);
      },
      undefined,
      (err) => {
        console.error("Error loading GLTF/GLB mesh:", err);
      }
    );
  }, [url, isLightMode]);

  if (!scene) return null;

  return <primitive object={scene} />;
}

export default function StlViewer({ url, loading, isLightMode }) {
  if (loading) {
    return (
      <div className={`empty-viewer flex-col ${isLightMode ? "light-mode" : ""}`} style={isLightMode ? { background: "#f8fafc" } : {}}>
        <div className="spinner"></div>
        <p className="mt-4 text-glow" style={isLightMode ? { color: "#1e293b", textShadow: "none" } : {}}>Computing CAD mesh in sandbox...</p>
      </div>
    );
  }

  if (!url) {
    return (
      <div className={`empty-viewer ${isLightMode ? "light-mode" : ""}`} style={isLightMode ? { background: "#f8fafc" } : {}}>
        <div className="empty-state-card text-center" style={isLightMode ? { background: "#ffffff", border: "1px solid #e2e8f0" } : {}}>
          <svg className="mx-auto h-12 w-12 text-gray-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
          </svg>
          <h3 style={isLightMode ? { color: "#1e293b" } : {}}>No Model Generated</h3>
          <p className="text-gray-400 max-w-sm mt-2" style={isLightMode ? { color: "#64748b" } : {}}>
            Enter a natural-language description of your mechanical part to compile it into 3D geometry.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="viewer-container">
      <Canvas shadows camera={{ position: [60, 60, 60], fov: 40 }}>
        <color attach="background" args={[isLightMode ? "#f8fafc" : "#0d0e12"]} />
        <ambientLight intensity={isLightMode ? 0.7 : 0.5} />
        
        {/* Front Directional Light with bias to prevent shadow acne */}
        <directionalLight
          position={[30, 40, 20]}
          intensity={isLightMode ? 1.0 : 0.8}
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
          shadow-bias={-0.0005}
        />
        
        {/* Back/Fill Directional Light */}
        <directionalLight
          position={[-30, -20, -20]}
          intensity={isLightMode ? 0.5 : 0.4}
        />
        
        {/* Soft Grid floor shadows */}
        <ContactShadows
          position={[0, -20, 0]}
          opacity={isLightMode ? 0.2 : 0.4}
          scale={100}
          blur={2.5}
          far={40}
        />
        
        <Center>
          <Model url={url} isLightMode={isLightMode} />
        </Center>
        
        <OrbitControls makeDefault enableDamping dampingFactor={0.05} />
      </Canvas>
      <div className="viewer-badge" style={isLightMode ? { background: "#e2e8f0", color: "#475569" } : {}}>3D Preview</div>
    </div>
  );
}
