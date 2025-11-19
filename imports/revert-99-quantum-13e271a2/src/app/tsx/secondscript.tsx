// ByteWordViz.js
import React, { useState, useEffect, useRef } from 'react';
import { ByteWord, QuineSystem, QuantumState, Morphology } from './firstscript';

// Color constants for visualization
const COLORS = {
  background: '#1a1a2e',
  byteWordFill: '#0f3460',
  byteWordStroke: '#e94560',
  byteWordText: '#ffffff',
  connectionLine: '#16213e',
  bitOn: '#ff4c29',
  bitOff: '#082032',
  morphismColors: [
    '#4361ee', // Identity
    '#3a0ca3', // Copy
    '#7209b7', // Increment
    '#f72585', // XNOR
    '#4cc9f0', // Toggle Control
    '#4895ef', // Swap Nibbles
    '#560bad', // Bitwise NOT
    '#f77f00'  // Random
  ]
};

// Utility function to describe morphism types
const getMorphismDescription = (morphism) => {
  switch(morphism) {
    case 0: return "Identity";
    case 1: return "Copy";
    case 2: return "Increment";
    case 3: return "XNOR";
    case 4: return "Toggle";
    case 5: return "Swap";
    case 6: return "NOT";
    case 7: return "Random";
    default: return "Unknown";
  }
};

// Component to visualize ByteWord bit patterns
const BitPattern = ({ byteWord }) => {
  const bits = byteWord.toString().replace(/\|/g, '').split('');

  return (
    <div className="flex">
      {bits.map((bit, idx) => (
        <div 
          key={idx} 
          className={`w-6 h-6 flex items-center justify-center text-xs font-mono
                     ${idx === 4 ? 'ml-2' : ''} 
                     ${bit === '1' ? 'bg-red-500 text-white' : 'bg-gray-200 text-gray-800'}`}
        >
          {bit}
        </div>
      ))}
    </div>
  );
};

// Canvas-based visualization component for ByteWord system
const ByteWordCanvas = ({ byteWords, width, height, animate = true }) => {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  
  // Calculate positions for each ByteWord in a circle
  const calculatePositions = (bwArray, canvasWidth, canvasHeight) => {
    const centerX = canvasWidth / 2;
    const centerY = canvasHeight / 2;
    const radius = Math.min(centerX, centerY) * 0.8;
    
    return bwArray.map((_, idx) => {
      const angle = (idx / bwArray.length) * Math.PI * 2;
      return {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    });
  };
  
  // Draw connection lines between ByteWords
  const drawConnections = (ctx, positions, byteWordsArray) => {
    ctx.lineWidth = 2;
    ctx.strokeStyle = COLORS.connectionLine;
    
    byteWordsArray.forEach((bw, idx) => {
      // Connect to the next ByteWord (target of transformation)
      const targetIdx = (idx + 1) % positions.length;
      const startPos = positions[idx];
      const endPos = positions[targetIdx];
      
      ctx.beginPath();
      ctx.moveTo(startPos.x, startPos.y);
      ctx.lineTo(endPos.x, endPos.y);
      
      // If this is a copy transform, draw a special arrow
      if (bw.morphism === 1) {
        ctx.strokeStyle = COLORS.morphismColors[1];
        // Draw arrowhead
        const angle = Math.atan2(endPos.y - startPos.y, endPos.x - startPos.x);
        const arrowSize = 10;
        ctx.lineTo(
          endPos.x - arrowSize * Math.cos(angle - Math.PI / 6),
          endPos.y - arrowSize * Math.sin(angle - Math.PI / 6)
        );
        ctx.moveTo(endPos.x, endPos.y);
        ctx.lineTo(
          endPos.x - arrowSize * Math.cos(angle + Math.PI / 6),
          endPos.y - arrowSize * Math.sin(angle + Math.PI / 6)
        );
      } else {
        ctx.strokeStyle = COLORS.morphismColors[bw.morphism];
      }
      
      ctx.stroke();
    });
  };
  
  // Draw ByteWords on the canvas
  const drawByteWords = (ctx, positions, byteWordsArray) => {
    const radius = 40;
    
    byteWordsArray.forEach((bw, idx) => {
      const { x, y } = positions[idx];
      
      // Draw ByteWord circle
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = COLORS.byteWordFill;
      ctx.fill();
      ctx.strokeStyle = COLORS.morphismColors[bw.morphism];
      ctx.lineWidth = 4;
      ctx.stroke();
      
      // Draw ByteWord ID and binary representation
      ctx.fillStyle = COLORS.byteWordText;
      ctx.font = '14px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(String.fromCharCode(65 + idx), x, y - 15);
      ctx.fillText(bw.toString(), x, y + 5);
      ctx.fillText(getMorphismDescription(bw.morphism), x, y + 25);
    });
  };
  
  // Draw bit pattern inside each ByteWord
  const drawBitPatterns = (ctx, positions, byteWordsArray) => {
    const bitSize = 5;
    const bitSpacing = 2;
    const totalWidth = 8 * (bitSize + bitSpacing) - bitSpacing;
    
    byteWordsArray.forEach((bw, idx) => {
      const { x, y } = positions[idx];
      const startX = x - totalWidth / 2;
      const startY = y + 35;
      
      // Get bit pattern
      const bits = bw.toString().replace(/\|/g, '').split('');
      
      bits.forEach((bit, bitIdx) => {
        const bitX = startX + bitIdx * (bitSize + bitSpacing);
        
        ctx.fillStyle = bit === '1' ? COLORS.bitOn : COLORS.bitOff;
        ctx.fillRect(bitX, startY, bitSize, bitSize);
      });
    });
  };
  
  // Animation frame handler
  const animate = (timestamp) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const positions = calculatePositions(byteWords, canvas.width, canvas.height);
    
    drawConnections(ctx, positions, byteWords);
    drawByteWords(ctx, positions, byteWords);
    drawBitPatterns(ctx, positions, byteWords);
    
    animationRef.current = requestAnimationFrame(animate);
  };
  
  // Set up canvas and animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    // Set canvas dimensions
    canvas.width = width;
    canvas.height = height;
    
    // Start animation loop
    if (animate) {
      animationRef.current = requestAnimationFrame(animate);
      
      return () => {
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      };
    } else {
      // Just draw once if not animating
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const positions = calculatePositions(byteWords, canvas.width, canvas.height);
      
      drawConnections(ctx, positions, byteWords);
      drawByteWords(ctx, positions, byteWords);
      drawBitPatterns(ctx, positions, byteWords);
    }
  }, [byteWords, width, height, animate]);
  
  return (
    <canvas 
      ref={canvasRef} 
      width={width} 
      height={height} 
      className="border border-gray-300 rounded shadow-lg"
    />
  );
};

// 3D Visualization using Three.js
const ByteWord3DVisualization = ({ byteWords, width, height }) => {
  const containerRef = useRef(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    // Import Three.js dynamically to avoid SSR issues
    const loadThreeJS = async () => {
      try {
        const THREE = await import('three');
        const OrbitControls = await import('three/examples/jsm/controls/OrbitControls');
        
        // Create scene
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(COLORS.background);
        
        // Create camera
        const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        camera.position.z = 200;
        
        // Create renderer
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(width, height);
        containerRef.current.appendChild(renderer.domElement);
        
        // Add controls
        const controls = new OrbitControls.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        
        // Add lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(0, 10, 10);
        scene.add(directionalLight);
        
        // Create ByteWord objects
        const byteWordObjects = byteWords.map((bw, idx) => {
          const angle = (idx / byteWords.length) * Math.PI * 2;
          const radius = 80;
          
          // Create a group for this ByteWord
          const group = new THREE.Group();
          
          // Add sphere for ByteWord
          const geometry = new THREE.SphereGeometry(10, 32, 32);
          const material = new THREE.MeshPhongMaterial({ 
            color: COLORS.morphismColors[bw.morphism],
            transparent: true,
            opacity: 0.8
          });
          const sphere = new THREE.Mesh(geometry, material);
          group.add(sphere);
          
          // Position in a circle
          group.position.x = radius * Math.cos(angle);
          group.position.y = radius * Math.sin(angle);
          
          // Add bits as small cubes
          const bits = bw.toString().replace(/\|/g, '').split('');
          bits.forEach((bit, bitIdx) => {
            if (bit === '1') {
              const bitGeometry = new THREE.BoxGeometry(2, 2, 2);
              const bitMaterial = new THREE.MeshPhongMaterial({ color: COLORS.bitOn });
              const cube = new THREE.Mesh(bitGeometry, bitMaterial);
              
              // Position bits in a circle around the sphere
              const bitAngle = (bitIdx / 8) * Math.PI * 2;
              cube.position.x = 15 * Math.cos(bitAngle);
              cube.position.y = 15 * Math.sin(bitAngle);
              
              group.add(cube);
            }
          });
          
          return group;
        });
        
        // Add ByteWord objects to scene
        byteWordObjects.forEach(obj => scene.add(obj));
        
        // Add connections between ByteWords
        byteWords.forEach((bw, idx) => {
          const startPos = byteWordObjects[idx].position;
          const targetIdx = (idx + 1) % byteWords.length;
          const endPos = byteWordObjects[targetIdx].position;
          
          // Create line for connection
          const points = [
            new THREE.Vector3(startPos.x, startPos.y, startPos.z),
            new THREE.Vector3(endPos.x, endPos.y, endPos.z)
          ];
          
          const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
          const lineMaterial = new THREE.LineBasicMaterial({ 
            color: COLORS.morphismColors[bw.morphism],
            linewidth: 2
          });
          
          const line = new THREE.Line(lineGeometry, lineMaterial);
          scene.add(line);
        });
        
        // Animation loop
        const animate = () => {
          requestAnimationFrame(animate);
          
          // Rotate ByteWord objects
          byteWordObjects.forEach(obj => {
            obj.rotation.x += 0.01;
            obj.rotation.y += 0.005;
          });
          
          controls.update();
          renderer.render(scene, camera);
        };
        
        animate();
        
        // Cleanup
        return () => {
          renderer.dispose();
          containerRef.current?.removeChild(renderer.domElement);
        };
      } catch (error) {
        console.error("Error loading Three.js:", error);
      }
    };
    
    loadThreeJS();
  }, [byteWords, width, height]);
  
  return <div ref={containerRef} className="border border-gray-300 rounded shadow-lg" />;
};

// Interactive ByteWord System Visualizer
const ByteWordVisualizer = () => {
  // QuineSystem initializations based on example from the first script
  const initialByteWords = [
    new ByteWord(0x29), // 0010|1001 - Copy Transform
    new ByteWord(0x35), // 0011|0101 - Swap Nibbles Transform
    new ByteWord(0x11)  // 0001|0001 - Copy Transform
  ];

  const [byteWords, setByteWords] = useState(initialByteWords);
  const [quineSystem, setQuineSystem] = useState(new QuineSystem(initialByteWords));
  const [visualizationType, setVisualizationType] = useState('2d'); // '2d' or '3d'
  const [autoPlay, setAutoPlay] = useState(false);
  const [speed, setSpeed] = useState(1000); // ms between steps
  const [showSystemInfo, setShowSystemInfo] = useState(true);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showEntropy, setShowEntropy] = useState(false);
  
  // Handle animation frames for autoplay
  useEffect(() => {
    let intervalId;
    if (autoPlay) {
      intervalId = setInterval(() => {
        runStep();
      }, speed);
    }
    return () => clearInterval(intervalId);
  }, [autoPlay, speed]);
  
  // Run a single step of the QuineSystem
  const runStep = () => {
    const newByteWords = quineSystem.step();
    setByteWords([...newByteWords]);
  };
  
  // Reset simulation to initial state
  const resetSimulation = () => {
    const system = new QuineSystem(initialByteWords);
    setQuineSystem(system);
    setByteWords([...initialByteWords]);
    setAutoPlay(false);
  };
  
  // Calculate entropy of the ByteWord system
  const calculateEntropy = () => {
    // Count occurrences of each ByteWord value
    const valueCounts = {};
    byteWords.forEach(bw => {
      valueCounts[bw.value] = (valueCounts[bw.value] || 0) + 1;
    });
    
    // Calculate Shannon entropy
    let entropy = 0;
    const totalByteWords = byteWords.length;
    
    Object.values(valueCounts).forEach(count => {
      const probability = count / totalByteWords;
      entropy -= probability * Math.log2(probability);
    });
    
    return entropy;
  };
  
  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold text-center mb-6">ByteWord Morphology Visualizer</h1>
      
      <div className="flex justify-between items-center mb-6">
        <div className="space-x-2">
          <button 
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
            onClick={runStep}
          >
            Step
          </button>
          <button 
            className={`px-4 py-2 rounded ${autoPlay ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-green-500 hover:bg-green-600 text-white'}`}
            onClick={() => setAutoPlay(!autoPlay)}
          >
            {autoPlay ? 'Pause' : 'Auto Play'}
          </button>
          <button 
            className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
            onClick={resetSimulation}
          >
            Reset
          </button>
        </div>
        
        <div className="flex items-center space-x-4">
          <div>
            <label className="mr-2 text-gray-700">Speed:</label>
            <input 
              type="range" 
              min="100" 
              max="2000" 
              step="100" 
              value={speed} 
              onChange={(e) => setSpeed(parseInt(e.target.value))} 
              className="w-32"
            />
            <span className="ml-2 text-gray-700">{speed}ms</span>
          </div>
          
          <select 
            value={visualizationType}
            onChange={(e) => setVisualizationType(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded"
          >
            <option value="2d">2D Visualization</option>
            <option value="3d">3D Visualization</option>
          </select>
        </div>
      </div>
      
      <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">System Visualization</h2>
          <div className="space-x-2">
            <button 
              className={`px-3 py-1 rounded text-sm ${showSystemInfo ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              onClick={() => setShowSystemInfo(!showSystemInfo)}
            >
              {showSystemInfo ? 'Hide Info' : 'Show Info'}
            </button>
            <button 
              className={`px-3 py-1 rounded text-sm ${showHeatmap ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              onClick={() => setShowHeatmap(!showHeatmap)}
            >
              {showHeatmap ? 'Hide Heatmap' : 'Show Heatmap'}
            </button>
            <button 
              className={`px-3 py-1 rounded text-sm ${showEntropy ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
              onClick={() => setShowEntropy(!showEntropy)}
            >
              {showEntropy ? 'Hide Entropy' : 'Show Entropy'}
            </button>
          </div>
        </div>
        
        {showSystemInfo && (
          <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded">
            <div>
              <span className="font-semibold">Current Step:</span> {quineSystem.currentStep}
            </div>
            <div>
              <span className="font-semibold">ByteWord Count:</span> {byteWords.length}
            </div>
            <div>
              <span className="font-semibold">System Entropy:</span> {calculateEntropy().toFixed(3)}
            </div>
          </div>
        )}
        
        <div className="flex justify-center">
          {visualizationType === '2d' ? (
            <ByteWordCanvas 
              byteWords={byteWords} 
              width={800} 
              height={600} 
              animate={true} 
            />
          ) : (
            <ByteWord3DVisualization 
              byteWords={byteWords} 
              width={800} 
              height={600} 
            />
          )}
        </div>
        
        {showEntropy && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold mb-2">Entropy Visualization</h3>
            <div className="w-full h-60 bg-gray-100 rounded border border-gray-300">
              {/* Entropy graph would go here */}
              <div className="h-full flex items-center justify-center">
                Entropy Visualization would render here
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4">ByteWord Details</h2>
        
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white">
            <thead>
              <tr className="bg-gray-100">
                <th className="py-2 px-4 border-b">ID</th>
                <th className="py-2 px-4 border-b">Binary Pattern</th>
                <th className="py-2 px-4 border-b">Value</th>
                <th className="py-2 px-4 border-b">T (State)</th>
                <th className="py-2 px-4 border-b">V (Morphism)</th>
                <th className="py-2 px-4 border-b">C (Control)</th>
                <th className="py-2 px-4 border-b">Function</th>
              </tr>
            </thead>
            <tbody>
              {byteWords.map((bw, idx) => (
                <tr key={idx} className={idx % 2 === 0 ? 'bg-gray-50' : ''}>
                  <td className="py-2 px-4 border-b text-center">{String.fromCharCode(65 + idx)}</td>
                  <td className="py-2 px-4 border-b">
                    <BitPattern byteWord={bw} />
                  </td>
                  <td className="py-2 px-4 border-b">{bw.value} ({bw.toHex()})</td>
                  <td className="py-2 px-4 border-b text-center">{bw.state_data}</td>
                  <td className="py-2 px-4 border-b text-center">{bw.morphism}</td>
                  <td className="py-2 px-4 border-b text-center">{bw.floor_morphic}</td>
                  <td className="py-2 px-4 border-b">
                    <span 
                      className="inline-block px-2 py-1 rounded text-white text-sm"
                      style={{ backgroundColor: COLORS.morphismColors[bw.morphism] }}
                    >
                      {getMorphismDescription(bw.morphism)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      <div className="mt-8 text-center text-gray-500 text-sm">
        ByteWord Morphology Visualizer
      </div>
    </div>
  );
};

export default ByteWordVisualizer;