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

// ByteWord class implementation
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

  // Deep clone a ByteWord
  clone() {
    const clone = new ByteWord(this.value);
    clone._refcount = this._refcount;
    clone._state = this._state;
    return clone;
  }

  // Transform based on morphism selector
  transform(targetWord) {
    // Clone the target to avoid unintended side effects
    const target = targetWord.clone();
    
    switch(this.morphism) {
      case 0: // Identity transform
        return target;
      case 1: // Copy transform
        return new ByteWord(this.value);
      case 2: // Increment transform
        return new ByteWord((target.value + 1) & 0xFF);
      case 3: // XNOR transform
        const newT = ByteWord.abelianTransform(
          target.state_data, 
          this.state_data, 
          this.floor_morphic
        );
        const newV = target.morphism;
        const newC = target.floor_morphic;
        return new ByteWord((newT << 4) | (newV << 1) | newC);
      case 4: // Toggle control bit
        return new ByteWord(target.value ^ 0x01);
      case 5: // Swap nibbles
        const high = target.state_data;
        const low = (target.morphism << 1) | target.floor_morphic;
        return new ByteWord((low << 4) | high);
      case 6: // Bitwise NOT
        return new ByteWord(~target.value & 0xFF);
      case 7: // Random transform
        return new ByteWord(Math.floor(Math.random() * 256));
      default:
        return target;
    }
  }
}

// Self-replicating pattern simulation
class QuineSystem {
  constructor(initialByteWords) {
    // Make deep copies of the initial ByteWords to avoid reference issues
    this.byteWords = initialByteWords.map(bw => bw instanceof ByteWord ? bw.clone() : new ByteWord(bw));
    this.replicationHistory = [this.byteWords.map(bw => bw.value)];
    this.currentStep = 0;
    this.transformationLog = [];
  }

  step() {
    if (this.byteWords.length === 0) return [];
    
    // Create a fresh log for this step
    const stepLog = [];
    
    // Create a copy of the current state
    const newByteWords = this.byteWords.map(bw => bw.clone());
    
    // Process each ByteWord based on its morphism
    for (let i = 0; i < this.byteWords.length; i++) {
      const current = this.byteWords[i];
      const targetIndex = (i + 1) % this.byteWords.length; // Point to next ByteWord
      const target = this.byteWords[targetIndex];
      
      // Log the current action
      const action = {
        sourceIndex: i,
        targetIndex,
        sourceBefore: current.value,
        targetBefore: target.value,
        morphism: current.morphism,
        operation: getMorphismDescription(current.morphism)
      };
      
      // Apply transformation based on the current ByteWord's morphism
      if (current.morphism === 1) { // Copy transform
        // Add a copy of the current ByteWord to the end (NOT the target)
        const newByteWord = new ByteWord(current.value);
        newByteWords.push(newByteWord);
        action.result = 'copy';
        action.newValue = newByteWord.value;
      } else {
        // Apply other transformations on the target
        const transformedByteWord = current.transform(target);
        newByteWords[targetIndex] = transformedByteWord;
        action.result = 'transform';
        action.targetAfter = transformedByteWord.value;
      }
      
      stepLog.push(action);
    }
    
    // Update system state
    this.byteWords = newByteWords;
    this.replicationHistory.push(this.byteWords.map(bw => bw.value));
    this.transformationLog.push(stepLog);
    this.currentStep++;
    
    return this.byteWords;
  }

  reset(initialByteWords) {
    // Make deep copies of the initial ByteWords
    this.byteWords = initialByteWords.map(bw => bw instanceof ByteWord ? bw.clone() : new ByteWord(bw));
    this.replicationHistory = [this.byteWords.map(bw => bw.value)];
    this.transformationLog = [];
    this.currentStep = 0;
  }
  
  // Get detailed logs of transformations
  getTransformationLogs() {
    return this.transformationLog;
  }
  
  // Analyze growth patterns
  analyzeGrowth() {
    const growthRates = [];
    for (let i = 1; i < this.replicationHistory.length; i++) {
      const previousCount = this.replicationHistory[i-1].length;
      const currentCount = this.replicationHistory[i].length;
      const growthRate = currentCount - previousCount;
      growthRates.push(growthRate);
    }
    return growthRates;
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

const ByteWordDisplay = ({ byteWord, index, highlightColor = null, showDetails = false }) => {
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
      {showDetails && (
        <div style={{ fontSize: '10px', marginTop: '5px', textAlign: 'center', color: '#555' }}>
          Hex: {byteWord.toHex()}, Pointable: {byteWord._pointable ? 'Yes' : 'No'}
        </div>
      )}
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
  
  const handleBinaryInput = (e) => {
    try {
      const binStr = e.target.value.replace(/[^01|]/g, '');
      if (binStr.length === 8 || binStr.length === 9) { // Allow for the separator
        const byteWord = ByteWord.fromString(binStr);
        setStateData(byteWord.state_data);
        setMorphism(byteWord.morphism);
        setFloorMorphic(byteWord.floor_morphic);
        onChange(byteWord);
      }
    } catch (error) {
      console.error("Invalid binary input", error);
    }
  };

  const updateByteWord = (t, v, c) => {
    const newValue = (t << 4) | (v << 1) | c;
    onChange(new ByteWord(newValue));
  };

  return (
    <div className="flex flex-col p-3 border border-gray-300 rounded">
      <div className="mb-2">
        <label className="block text-sm font-medium">Binary Representation:</label>
        <input
          type="text"
          placeholder="TTTT|VVVC (e.g. 0010|1001)"
          value={`${stateData.toString(2).padStart(4, '0')}|${morphism.toString(2).padStart(3, '0')}${floorMorphic}`}
          onChange={handleBinaryInput}
          className="w-full p-1 border border-gray-300 rounded font-mono"
        />
      </div>
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

// Add a component to visualize transformations
const TransformationVisualizer = ({ quineSystem }) => {
  const logs = quineSystem.getTransformationLogs();
  
  if (!logs || logs.length === 0) {
    return <div className="text-center text-gray-500">No transformation logs available yet.</div>;
  }
  
  return (
    <div className="mt-4">
      <h3 className="text-lg font-semibold mb-2">Transformation Logs</h3>
      <div className="overflow-x-auto">
        {logs.map((stepLog, stepIndex) => (
          <div key={stepIndex} className="mb-4 border-b pb-2">
            <h4 className="font-medium">Step {stepIndex + 1}</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {stepLog.map((action, actionIndex) => (
                <div key={actionIndex} className="border p-2 rounded text-sm">
                  <div>
                    ByteWord {String.fromCharCode(65 + action.sourceIndex)} 
                    ({action.operation}) → 
                    ByteWord {String.fromCharCode(65 + action.targetIndex)}
                  </div>
                  {action.result === 'copy' ? (
                    <div className="text-green-600">
                      Copied ByteWord {String.fromCharCode(65 + action.sourceIndex)} (value: {action.sourceBefore})
                    </div>
                  ) : (
                    <div className="text-blue-600">
                      Transformed {action.targetBefore} → {action.targetAfter}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Growth Analysis Component
const GrowthAnalysis = ({ quineSystem }) => {
  const growthRates = quineSystem.analyzeGrowth();
  
  if (growthRates.length === 0) {
    return <div className="text-center text-gray-500">No growth data available yet.</div>;
  }
  
  return (
    <div className="mt-4">
      <h3 className="text-lg font-semibold mb-2">Growth Analysis</h3>
      <div>
        <p className="text-sm mb-2">ByteWords added per step:</p>
        <div className="flex flex-wrap gap-2">
          {growthRates.map((rate, index) => (
            <div key={index} className={`px-3 py-1 rounded text-white text-sm ${rate > 0 ? 'bg-green-600' : rate < 0 ? 'bg-red-600' : 'bg-gray-500'}`}>
              Step {index + 1}: {rate > 0 ? `+${rate}` : rate}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-2">
        <p className="text-sm">Total ByteWords: {quineSystem.byteWords.length}</p>
      </div>
    </div>
  );
};

// Create a main component to integrate everything
const QuineSystemSimulator = () => {
  const [initialByteWords, setInitialByteWords] = useState([
    new ByteWord(0x29),  // 0010|1001 - Copy Transform (morphism = 4)
    new ByteWord(0x35),  // 0011|0101 - Swap Nibbles (morphism = 2)
    new ByteWord(0x11)   // 0001|0001 - Identity (morphism = 0)
  ]);
  
  const [quineSystem, setQuineSystem] = useState(null);
  const [activeByteWordIndex, setActiveByteWordIndex] = useState(-1);
  const [showDetails, setShowDetails] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [stepInterval, setStepInterval] = useState(1000); // 1 second by default
  
  // Initialize the QuineSystem
  useEffect(() => {
    setQuineSystem(new QuineSystem(initialByteWords));
  }, []);
  
  // Handle continuous running
  useEffect(() => {
    let intervalId;
    
    if (isRunning && quineSystem) {
      intervalId = setInterval(() => {
        setQuineSystem(prevSystem => {
          const cloneSystem = new QuineSystem(prevSystem.byteWords);
          cloneSystem.replicationHistory = [...prevSystem.replicationHistory];
          cloneSystem.transformationLog = [...prevSystem.transformationLog];
          cloneSystem.currentStep = prevSystem.currentStep;
          cloneSystem.step();
          return cloneSystem;
        });
      }, stepInterval);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isRunning, stepInterval, quineSystem]);
  
  const handleEditByteWord = (index, byteWord) => {
    const newInitialWords = [...initialByteWords];
    newInitialWords[index] = byteWord;
    setInitialByteWords(newInitialWords);
    
    if (quineSystem) {
      const newSystem = new QuineSystem(newInitialWords);
      setQuineSystem(newSystem);
    }
  };
  
  const handleAddByteWord = () => {
    // Add a new ByteWord with random value
    const randomValue = Math.floor(Math.random() * 256);
    const newByteWord = new ByteWord(randomValue);
    
    setInitialByteWords(prev => [...prev, newByteWord]);
    
    if (quineSystem) {
      const newSystem = new QuineSystem([...initialByteWords, newByteWord]);
      setQuineSystem(newSystem);
    }
  };
  
  const handleRemoveByteWord = (index) => {
    if (initialByteWords.length <= 1) return; // Keep at least one ByteWord
    
    const newInitialWords = initialByteWords.filter((_, i) => i !== index);
    setInitialByteWords(newInitialWords);
    
    if (quineSystem) {
      const newSystem = new QuineSystem(newInitialWords);
      setQuineSystem(newSystem);
    }
    
    if (activeByteWordIndex === index) {
      setActiveByteWordIndex(-1);
    }
  };
  
  const handleStep = () => {
    if (quineSystem) {
      setQuineSystem(prevSystem => {
        const cloneSystem = new QuineSystem(prevSystem.byteWords);
        cloneSystem.replicationHistory = [...prevSystem.replicationHistory];
        cloneSystem.transformationLog = [...prevSystem.transformationLog];
        cloneSystem.currentStep = prevSystem.currentStep;
        cloneSystem.step();
        return cloneSystem;
      });
    }
  };
  
  const handleReset = () => {
    setIsRunning(false);
    if (quineSystem) {
      setQuineSystem(new QuineSystem(initialByteWords));
    }
  };
  
  if (!quineSystem) {
    return <div className="text-center p-8">Loading simulator...</div>;
  }
  
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">ByteWord Self-Replicating System</h1>
      
      <div className="mb-6 bg-blue-50 p-4 rounded shadow-sm">
        <h2 className="text-lg font-semibold mb-2">Initial Configuration</h2>
        <div className="flex flex-wrap gap-4">
          {initialByteWords.map((byteWord, index) => (
            <div key={index} className="relative">
              <ByteWordDisplay 
                byteWord={byteWord} 
                index={index} 
                highlightColor={activeByteWordIndex === index ? '#e6f7ff' : null}
                showDetails={showDetails}
              />
              <div className="flex justify-between mt-2">
                <button 
                  onClick={() => setActiveByteWordIndex(index)}
                  className="px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600"
                >
                  Edit
                </button>
                <button 
                  onClick={() => handleRemoveByteWord(index)}
                  className="px-2 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
          <div className="flex items-center">
            <button 
              onClick={handleAddByteWord}
              className="px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              + Add ByteWord
            </button>
          </div>
        </div>
        
        {activeByteWordIndex >= 0 && (
          <div className="mt-4 p-4 border rounded bg-white">
            <h3 className="font-medium mb-2">Edit ByteWord {String.fromCharCode(65 + activeByteWordIndex)}</h3>
            <ByteWordEditor 
              byteWord={initialByteWords[activeByteWordIndex]} 
              onChange={(byteWord) => handleEditByteWord(activeByteWordIndex, byteWord)}
            />
          </div>
        )}
      </div>
      
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Simulation Controls</h2>
        <div className="flex items-center gap-4">
          <button 
            onClick={handleStep}
            disabled={isRunning}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
          >
            Step
          </button>
          <button 
            onClick={() => setIsRunning(!isRunning)}
            className={`px-4 py-2 ${isRunning ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'} text-white rounded`}
          >
            {isRunning ? 'Pause' : 'Run'}
          </button>
          <button 
            onClick={handleReset}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Reset
          </button>
          <div className="ml-4">
            <label className="block text-sm font-medium mb-1">Step Interval (ms):</label>
            <input
              type="number"
              min="100"
              max="5000"
              step="100"
              value={stepInterval}
              onChange={(e) => setStepInterval(Math.max(100, parseInt(e.target.value, 10) || 1000))}
              className="w-24 p-1 border border-gray-300 rounded"
            />
          </div>
          <div className="ml-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={showDetails}
                onChange={() => setShowDetails(!showDetails)}
                className="mr-2"
              />
              <span className="text-sm">Show Details</span>
            </label>
          </div>
        </div>
      </div>
      
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Current State (Step {quineSystem.currentStep})</h2>
        <div className="flex flex-wrap gap-4 overflow-y-auto" style={{ maxHeight: '400px' }}>
          {quineSystem.byteWords.map((byteWord, index) => (
            <ByteWordDisplay 
              key={index}
              byteWord={byteWord} 
              index={index}
              showDetails={showDetails}
            />
          ))}
          {quineSystem.byteWords.length === 0 && (
            <div className="text-gray-500">No ByteWords in the system.</div>
          )}
        </div>
      </div>
      
      <div className="mb-6">
        <GrowthAnalysis quineSystem={quineSystem} />
      </div>
      
      <div className="mb-6">
        <TransformationVisualizer quineSystem={quineSystem} />
      </div>
    </div>
  );
};

export default QuineSystemSimulator;