import React, { useState, useEffect } from 'react';

// Enum for quantum state
const QuantumState = {
  SUPERPOSITION: 'SUPERPOSITION',
  ENTANGLED: 'ENTANGLED',
  COLLAPSED: 'COLLAPSED'
};

// Enum for morphology
const Morphology = {
  STATIC: 0,
  DYNAMIC: 1
};

// ByteWord class implementation with bug fixes
class ByteWord {
  constructor(raw) {
    if (raw < 0 || raw > 255) {
      throw new Error("ByteWord must be an 8-bit integer (0-255)");
    }
    this.raw = raw;
    this.value = raw & 0xFF;
    this.state_data = (raw >> 4) & 0x0F;    // T: High nibble (4 bits)
    this.morphism = (raw >> 1) & 0x07;      // V: Middle 3 bits
    this.floor_morphic = raw & 0x01;        // C: Least significant bit
    this._refcount = 1;
    this._state = QuantumState.SUPERPOSITION;
  }

  get _pointable() {
    return this.floor_morphic === Morphology.DYNAMIC;
  }

  toString() {
    return `${this.state_data.toString(2).padStart(4, '0')}|${this.morphism.toString(2).padStart(3, '0')}${this.floor_morphic}`;
  }

  toHex() {
    return `0x${this.value.toString(16).padStart(2, '0')}`;
  }

  // Return a deep copy of this ByteWord
  clone() {
    return new ByteWord(this.value);
  }

  static xnor(a, b, width = 4) {
    return ~(a ^ b) & ((1 << width) - 1);
  }

  static abelianTransform(t, v, c) {
    if (c === 1) {
      return ByteWord.xnor(t, v);  // Apply XNOR transformation
    }
    return t;  // Identity morphism when c = 0
  }

  static fromString(binStr) {
    // Parse a string like "0010|1001"
    binStr = binStr.replace(/[^01]/g, '');
    if (binStr.length !== 8) {
      throw new Error("Binary string must be 8 bits");
    }
    return new ByteWord(parseInt(binStr, 2));
  }

  // Transform based on morphism selector
  transform(targetWord) {
    switch(this.morphism) {
      case 0: // Identity transform
        return targetWord.clone();
      case 1: // Copy transform
        return this.clone();
      case 2: // Increment transform
        return new ByteWord((targetWord.value + 1) & 0xFF);
      case 3: // XNOR transform
        const newT = ByteWord.abelianTransform(
          targetWord.state_data, 
          this.state_data, 
          this.floor_morphic
        );
        const newV = targetWord.morphism;
        const newC = targetWord.floor_morphic;
        return new ByteWord((newT << 4) | (newV << 1) | newC);
      case 4: // Toggle control bit
        return new ByteWord(targetWord.value ^ 0x01);
      case 5: // Swap nibbles
        const high = targetWord.state_data;
        const low = (targetWord.morphism << 1) | targetWord.floor_morphic;
        return new ByteWord((low << 4) | high);
      case 6: // Bitwise NOT
        return new ByteWord(~targetWord.value & 0xFF);
      case 7: // Random transform
        return new ByteWord(Math.floor(Math.random() * 256));
      default:
        return targetWord.clone();
    }
  }
}

// Enhanced QuineSystem class with debugging and visualization capabilities
class QuineSystem {
  constructor(initialByteWords) {
    this.byteWords = initialByteWords.map(bw => bw.clone());
    this.replicationHistory = [this.byteWords.map(bw => ({ 
      value: bw.value,
      morphism: bw.morphism 
    }))];
    this.currentStep = 0;
    this.transformationLog = [];
  }

  step() {
    if (this.byteWords.length === 0) return;
    
    // Create a copy of the current state
    const newByteWords = [...this.byteWords];
    const stepLog = [];
    
    // Process each ByteWord based on its morphism
    for (let i = 0; i < this.byteWords.length; i++) {
      const current = this.byteWords[i];
      const targetIndex = (i + 1) % this.byteWords.length; // Point to next ByteWord
      const target = this.byteWords[targetIndex];
      
      // Apply transformation based on the current ByteWord's morphism
      if (current.morphism === 1) { // Copy transform
        // Create a proper clone of the target and add it to the end
        const copy = target.clone();
        newByteWords.push(copy);
        
        stepLog.push({
          sourceIndex: i,
          targetIndex: targetIndex,
          action: 'copy',
          result: copy.value
        });
      } else {
        // Apply other transformations on the target
        const transformed = current.transform(target);
        newByteWords[targetIndex] = transformed;
        
        stepLog.push({
          sourceIndex: i,
          targetIndex: targetIndex,
          action: 'transform',
          morphism: current.morphism,
          result: transformed.value
        });
      }
    }
    
    this.byteWords = newByteWords;
    this.replicationHistory.push(this.byteWords.map(bw => ({ 
      value: bw.value,
      morphism: bw.morphism 
    })));
    this.transformationLog.push(stepLog);
    this.currentStep++;
    
    return this.byteWords;
  }

  reset(initialByteWords) {
    this.byteWords = initialByteWords.map(bw => bw.clone());
    this.replicationHistory = [this.byteWords.map(bw => ({ 
      value: bw.value,
      morphism: bw.morphism 
    }))];
    this.transformationLog = [];
    this.currentStep = 0;
  }
  
  // Get entropy of the current state
  calculateEntropy() {
    const valueCounts = {};
    this.byteWords.forEach(bw => {
      valueCounts[bw.value] = (valueCounts[bw.value] || 0) + 1;
    });
    
    let entropy = 0;
    const totalWords = this.byteWords.length;
    
    for (const count of Object.values(valueCounts)) {
      const probability = count / totalWords;
      entropy -= probability * Math.log2(probability);
    }
    
    return entropy;
  }
}

// Transform description based on morphism value
const getMorphismDescription = (morphism) => {
  switch(morphism) {
    case 0: return "Identity (No Change)";
    case 1: return "Copy Transform";
    case 2: return "Increment";
    case 3: return "XNOR Transform";
    case 4: return "Toggle Control";
    case 5: return "Swap Nibbles";
    case 6: return "Bitwise NOT";
    case 7: return "Random Transform";
    default: return "Unknown";
  }
};

const ByteWordDisplay = ({ byteWord, index, highlightColor = null }) => {
  const style = {
    border: '2px solid #0066cc',
    borderRadius: '5px',
    padding: '8px',
    margin: '5px',
    minWidth: '120px',
    backgroundColor: highlightColor || '#fff',
    position: 'relative'
  };

  return (
    <div style={style}>
      <div style={{ position: 'absolute', top: '-20px', fontSize: '12px' }}>
        ByteWord {String.fromCharCode(65 + index)} ({byteWord.value})
      </div>
      <div style={{ fontFamily: 'Courier New', fontSize: '16px', textAlign: 'center' }}>
        {byteWord.toString()}
      </div>
      <div style={{ fontSize: '10px', marginTop: '5px', textAlign: 'center' }}>
        T:{byteWord.state_data} V:{byteWord.morphism} C:{byteWord.floor_morphic}
      </div>
      <div style={{ fontSize: '12px', marginTop: '5px', textAlign: 'center' }}>
        {getMorphismDescription(byteWord.morphism)}
      </div>
    </div>
  );
};

const ByteWordEditor = ({ byteWord, onChange }) => {
  const [stateData, setStateData] = useState(byteWord.state_data);
  const [morphism, setMorphism] = useState(byteWord.morphism);
  const [floorMorphic, setFloorMorphic] = useState(byteWord.floor_morphic);

  const handleStateDataChange = (e) => {
    const value = parseInt(e.target.value, 10);
    if (isNaN(value) || value < 0 || value > 15) return;
    setStateData(value);
    updateByteWord(value, morphism, floorMorphic);
  };

  const handleMorphismChange = (e) => {
    const value = parseInt(e.target.value, 10);
    if (isNaN(value) || value < 0 || value > 7) return;
    setMorphism(value);
    updateByteWord(stateData, value, floorMorphic);
  };

  const handleFloorMorphicChange = (e) => {
    const value = parseInt(e.target.value, 10);
    if (isNaN(value) || (value !== 0 && value !== 1)) return;
    setFloorMorphic(value);
    updateByteWord(stateData, morphism, value);
  };

  const updateByteWord = (t, v, c) => {
    const newValue = (t << 4) | (v << 1) | c;
    onChange(new ByteWord(newValue));
  };

  return (
    <div className="flex flex-col p-3 border border-gray-300 rounded">
      <div className="mb-2">
        <label className="block text-sm font-medium">State Data (T - 4 bits):</label>
        <input
          type="number"
          min="0"
          max="15"
          value={stateData}
          onChange={handleStateDataChange}
          className="w-full p-1 border border-gray-300 rounded"
        />
      </div>
      <div className="mb-2">
        <label className="block text-sm font-medium">Morphism (V - 3 bits):</label>
        <select
          value={morphism}
          onChange={handleMorphismChange}
          className="w-full p-1 border border-gray-300 rounded"
        >
          <option value="0">0 - Identity</option>
          <option value="1">1 - Copy</option>
          <option value="2">2 - Increment</option>
          <option value="3">3 - XNOR</option>
          <option value="4">4 - Toggle Control</option>
          <option value="5">5 - Swap Nibbles</option>
          <option value="6">6 - Bitwise NOT</option>
          <option value="7">7 - Random</option>
        </select>
      </div>
      <div className="mb-2">
        <label className="block text-sm font-medium">Control Bit (C - 1 bit):</label>
        <select
          value={floorMorphic}
          onChange={handleFloorMorphicChange}
          className="w-full p-1 border border-gray-300 rounded"
        >
          <option value="0">0 - Static</option>
          <option value="1">1 - Dynamic</option>
        </select>
      </div>
    </div>
  );
};

// New component to visualize transformation chains
const TransformationGraph = ({ quineSystem }) => {
    if (!quineSystem.transformationLog || quineSystem.transformationLog.length === 0) {
      return <div className="text-gray-500 p-4">No transformation data available yet. Run the simulation to view transformations.</div>;
    }
  
    const renderTransformationStep = (step, stepIndex) => {
      return (
        <div key={stepIndex} className="mb-4 p-2 border border-gray-300 rounded">
          <h4 className="text-sm font-bold">Step {stepIndex + 1}</h4>
          <div className="flex flex-wrap gap-2">
            {step.map((transform, idx) => (
              <div key={idx} className="text-xs p-2 bg-gray-100 rounded">
                <div>Source: {String.fromCharCode(65 + transform.sourceIndex)} → Target: {String.fromCharCode(65 + transform.targetIndex)}</div>
                <div>{transform.action === 'copy' ? 'COPY' : `Transform (${getMorphismDescription(transform.morphism)})`}</div>
                <div>Result: {transform.result}</div>
              </div>
            ))}
          </div>
        </div>
      );
    };
  
    return (
      <div className="mt-4 p-3 border border-gray-300 rounded max-h-64 overflow-y-auto">
        <h3 className="text-lg font-bold mb-2">Transformation History</h3>
        {quineSystem.transformationLog.map(renderTransformationStep)}
      </div>
    );
  };
  
  // New component to show system metrics
  const SystemMetrics = ({ quineSystem }) => {
    const entropy = quineSystem.calculateEntropy();
    const growth = quineSystem.replicationHistory.length > 1 
      ? quineSystem.replicationHistory[quineSystem.replicationHistory.length - 1].length - 
        quineSystem.replicationHistory[0].length 
      : 0;
    
    return (
      <div className="grid grid-cols-3 gap-4 p-3 border border-gray-300 rounded mt-4">
        <div className="text-center">
          <div className="text-sm font-semibold">Current Step</div>
          <div className="text-xl">{quineSystem.currentStep}</div>
        </div>
        <div className="text-center">
          <div className="text-sm font-semibold">ByteWord Count</div>
          <div className="text-xl">{quineSystem.byteWords.length}</div>
        </div>
        <div className="text-center">
          <div className="text-sm font-semibold">Growth</div>
          <div className="text-xl">{growth}</div>
        </div>
        <div className="text-center col-span-3">
          <div className="text-sm font-semibold">Entropy</div>
          <div className="text-xl">{entropy.toFixed(3)}</div>
        </div>
      </div>
    );
  };
  
  // Visualization for the replication history
  const ReplicationHistory = ({ quineSystem }) => {
    if (quineSystem.replicationHistory.length <= 1) {
      return <div className="text-gray-500 p-4">Run the simulation to see replication history.</div>;
    }
  
    return (
      <div className="mt-4 p-3 border border-gray-300 rounded max-h-64 overflow-y-auto">
        <h3 className="text-lg font-bold mb-2">Replication History</h3>
        {quineSystem.replicationHistory.map((state, idx) => (
          <div key={idx} className="mb-2 p-2 bg-gray-100 rounded text-xs">
            <div className="font-bold mb-1">Step {idx}</div>
            <div className="flex flex-wrap gap-1">
              {state.map((bw, bwIdx) => (
                <div key={bwIdx} className="p-1 bg-white rounded border border-gray-300">
                  {String.fromCharCode(65 + bwIdx)}: {bw.value} (M:{bw.morphism})
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };
  
  // Main Application Component
  const QuineSystemApp = () => {
    const [byteWords, setByteWords] = useState([
      new ByteWord(0x21), // 00100001 (Morphism 0, Identity)
      new ByteWord(0x33), // 00110011 (Morphism 1, Copy)
      new ByteWord(0x45)  // 01000101 (Morphism 2, Increment)
    ]);
    
    const [quineSystem, setQuineSystem] = useState(() => new QuineSystem(byteWords));
    const [autoRunning, setAutoRunning] = useState(false);
    const [autoRunSpeed, setAutoRunSpeed] = useState(1000); // ms
    const [selectedByteWordIndex, setSelectedByteWordIndex] = useState(null);
    const autoRunRef = React.useRef(null);
    
    useEffect(() => {
      // Reset quineSystem when byteWords change
      setQuineSystem(new QuineSystem(byteWords));
      
      // Cleanup auto-run if active
      return () => {
        if (autoRunRef.current) {
          clearInterval(autoRunRef.current);
        }
      };
    }, [byteWords]);
  
    useEffect(() => {
      // Handle auto-running
      if (autoRunning) {
        autoRunRef.current = setInterval(() => {
          setQuineSystem(prevSystem => {
            const newSystem = new QuineSystem([...prevSystem.byteWords]);
            newSystem.replicationHistory = [...prevSystem.replicationHistory];
            newSystem.transformationLog = [...prevSystem.transformationLog];
            newSystem.currentStep = prevSystem.currentStep;
            newSystem.step();
            return newSystem;
          });
        }, autoRunSpeed);
      } else if (autoRunRef.current) {
        clearInterval(autoRunRef.current);
        autoRunRef.current = null;
      }
      
      return () => {
        if (autoRunRef.current) {
          clearInterval(autoRunRef.current);
        }
      };
    }, [autoRunning, autoRunSpeed]);
  
    const handleAddByteWord = () => {
      const newByteWord = new ByteWord(Math.floor(Math.random() * 256));
      setByteWords([...byteWords, newByteWord]);
    };
  
    const handleRemoveByteWord = (index) => {
      if (byteWords.length <= 1) return;
      const newByteWords = [...byteWords];
      newByteWords.splice(index, 1);
      setByteWords(newByteWords);
      if (selectedByteWordIndex === index) {
        setSelectedByteWordIndex(null);
      }
    };
  
    const handleByteWordChange = (index, newByteWord) => {
      const newByteWords = [...byteWords];
      newByteWords[index] = newByteWord;
      setByteWords(newByteWords);
    };
  
    const handleStep = () => {
      setQuineSystem(prevSystem => {
        const newSystem = new QuineSystem([...prevSystem.byteWords]);
        newSystem.replicationHistory = [...prevSystem.replicationHistory];
        newSystem.transformationLog = [...prevSystem.transformationLog];
        newSystem.currentStep = prevSystem.currentStep;
        newSystem.step();
        return newSystem;
      });
    };
  
    const handleReset = () => {
      setQuineSystem(new QuineSystem(byteWords));
      setAutoRunning(false);
    };
  
    return (
      <div className="p-4">
        <h1 className="text-2xl font-bold mb-4">Quine System Simulator</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="col-span-1 lg:col-span-2 p-4 border border-gray-300 rounded">
            <h2 className="text-xl font-bold mb-3">ByteWords</h2>
            
            <div className="flex flex-wrap mb-4">
              {byteWords.map((bw, index) => (
                <div key={index} className="relative">
                  <ByteWordDisplay 
                    byteWord={bw}
                    index={index}
                    highlightColor={selectedByteWordIndex === index ? '#e6f7ff' : null}
                  />
                  <div className="absolute top-0 right-0">
                    <button 
                      className="text-red-500 font-bold p-1" 
                      onClick={() => handleRemoveByteWord(index)}
                    >
                      ×
                    </button>
                  </div>
                  <button 
                    className="text-xs mt-1 p-1 bg-blue-100 rounded" 
                    onClick={() => setSelectedByteWordIndex(index === selectedByteWordIndex ? null : index)}
                  >
                    {index === selectedByteWordIndex ? 'Close Editor' : 'Edit'}
                  </button>
                </div>
              ))}
              <div className="flex items-center">
                <button 
                  className="ml-4 p-2 bg-green-500 text-white rounded" 
                  onClick={handleAddByteWord}
                >
                  + Add ByteWord
                </button>
              </div>
            </div>
            
            {selectedByteWordIndex !== null && (
              <div className="mb-4 p-3 border border-blue-300 rounded bg-blue-50">
                <h3 className="text-lg font-bold mb-2">
                  Edit ByteWord {String.fromCharCode(65 + selectedByteWordIndex)}
                </h3>
                <ByteWordEditor 
                  byteWord={byteWords[selectedByteWordIndex]}
                  onChange={(newBW) => handleByteWordChange(selectedByteWordIndex, newBW)}
                />
              </div>
            )}
            
            <div className="flex flex-wrap gap-2 mb-4">
              <button 
                className="p-2 bg-blue-500 text-white rounded"
                onClick={handleStep}
              >
                Step
              </button>
              <button 
                className={`p-2 ${autoRunning ? 'bg-red-500' : 'bg-green-500'} text-white rounded`}
                onClick={() => setAutoRunning(!autoRunning)}
              >
                {autoRunning ? 'Stop' : 'Auto Run'}
              </button>
              <button 
                className="p-2 bg-gray-500 text-white rounded"
                onClick={handleReset}
              >
                Reset
              </button>
              
              <div className="flex items-center ml-4">
                <label className="mr-2 text-sm">Speed:</label>
                <input 
                  type="range" 
                  min="100" 
                  max="2000" 
                  step="100"
                  value={autoRunSpeed}
                  onChange={(e) => setAutoRunSpeed(parseInt(e.target.value))}
                  className="w-32"
                />
                <span className="ml-2 text-sm">{autoRunSpeed}ms</span>
              </div>
            </div>
            
            <SystemMetrics quineSystem={quineSystem} />
          </div>
          
          <div className="col-span-1 p-4 border border-gray-300 rounded">
            <h2 className="text-xl font-bold mb-3">Analysis</h2>
            <ReplicationHistory quineSystem={quineSystem} />
            <TransformationGraph quineSystem={quineSystem} />
          </div>
        </div>
        
        <div className="mt-4 p-4 border border-gray-300 rounded bg-gray-50">
          <h2 className="text-xl font-bold mb-3">Documentation</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-lg font-semibold mb-2">ByteWord Structure</h3>
              <p className="mb-2">Each ByteWord is an 8-bit value with the following structure:</p>
              <ul className="list-disc ml-5 mb-3">
                <li><strong>T (State Data):</strong> High 4 bits (bits 7-4)</li>
                <li><strong>V (Morphism):</strong> Middle 3 bits (bits 3-1)</li>
                <li><strong>C (Control):</strong> Low 1 bit (bit 0)</li>
              </ul>
              <p>Example: Binary 00101001 (0x29)</p>
              <ul className="list-disc ml-5">
                <li>T = 0010 (2)</li>
                <li>V = 100 (4)</li>
                <li>C = 1</li>
              </ul>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold mb-2">Transformations</h3>
              <ul className="list-disc ml-5">
                <li><strong>0 - Identity:</strong> No change to target</li>
                <li><strong>1 - Copy:</strong> Creates a copy of the target</li>
                <li><strong>2 - Increment:</strong> Increments target's value</li>
                <li><strong>3 - XNOR:</strong> Applies XNOR between states</li>
                <li><strong>4 - Toggle:</strong> Toggles target's control bit</li>
                <li><strong>5 - Swap:</strong> Swaps target's nibbles</li>
                <li><strong>6 - NOT:</strong> Bitwise NOT of target</li>
                <li><strong>7 - Random:</strong> Randomizes target</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };
  
  // Export the main component
  export default QuineSystemApp;