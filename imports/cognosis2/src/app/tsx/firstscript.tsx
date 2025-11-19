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

  selectTarget(byteWords, currentIndex) {
    if (this._pointable) {
      // Dynamic targeting based on state_data value
      return this.state_data % byteWords.length;
    } else {
      // Default static targeting (next in sequence)
      return (currentIndex + 1) % byteWords.length;
    }
  }

  // Transform based on morphism selector
  transform(targetWord) {
    switch(this.morphism) {
      case 0: // Identity transform
        return targetWord;
      case 1: // Copy transform
        return new ByteWord(this.value);
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
        return new ByteWord((low << 4) | (high << 0));
      case 6: // Bitwise NOT
        return new ByteWord(~targetWord.value & 0xFF);
      case 7: // Random transform
        return new ByteWord(Math.floor(Math.random() * 256));
      default:
        return targetWord;
    }
  }
}

// Self-replicating pattern simulation
class QuineSystem {
  constructor(initialByteWords) {
    this.byteWords = [...initialByteWords];
    this.replicationHistory = [this.byteWords.map(bw => bw.value)];
    this.currentStep = 0;
  }

  detectCycle() {
    // Look for repeating patterns in replication history
    const currentState = JSON.stringify(this.byteWords.map(bw => bw.value));
    return this.replicationHistory.findIndex(state => 
      JSON.stringify(state) === currentState
    );
  }

  step() {
    if (this.byteWords.length === 0) return;
    
    // Create a copy of the current state
    const newByteWords = [...this.byteWords];
    const originalLength = this.byteWords.length;
    
    // Process only the original ByteWords in this step
    for (let i = 0; i < originalLength; i++) {
      const current = this.byteWords[i];
      const targetIndex = (i + 1) % originalLength; // Point to next original ByteWord
      const target = this.byteWords[targetIndex];
      
      // Apply transformation based on the current ByteWord's morphism
      if (current.morphism === 1) { // Copy transform
        // Add a copy of the target to the end
        newByteWords.push(new ByteWord(target.value));
      } else {
        // Apply other transformations on the target
        newByteWords[targetIndex] = current.transform(target);
      }
    }
    
    this.byteWords = newByteWords;
    this.replicationHistory.push(this.byteWords.map(bw => bw.value));
    this.currentStep++;
    
    return this.byteWords;
  }
  calculateEntropy() {
    const values = this.byteWords.map(bw => bw.value);
    const frequencies = {};
    // Count occurrences
    values.forEach(val => {
      frequencies[val] = (frequencies[val] || 0) + 1;
    });
    // Calculate entropy
    return Object.values(frequencies).reduce((entropy, freq) => {
      const p = freq / values.length;
      return entropy - p * Math.log2(p);
    }, 0);
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

const ByteWordPlayground = () => {
  // QuineSystem initializations based on your SVG example
  const initialByteWords = [
    new ByteWord(0x29), // 0010|1001 - Copy Transform
    new ByteWord(0x35), // 0011|0101 - Increment Transform
    new ByteWord(0x11)  // 0001|0001 - Toggle Control
  ];

  const [byteWords, setByteWords] = useState(initialByteWords);
  const [quineSystem, setQuineSystem] = useState(new QuineSystem(initialByteWords));
  const [autoPlay, setAutoPlay] = useState(false);
  const [speed, setSpeed] = useState(1000); // ms between steps
  const [editIndex, setEditIndex] = useState(null);
  const [highlightIndex, setHighlightIndex] = useState(null);
  const [displayMode, setDisplayMode] = useState('visual'); // 'visual' or 'table'
  const [showReplicationHistory, setShowReplicationHistory] = useState(false);

  useEffect(() => {
    let intervalId;
    if (autoPlay) {
      intervalId = setInterval(() => {
        runStep();
      }, speed);
    }
    return () => clearInterval(intervalId);
  }, [autoPlay, speed, quineSystem]);

  const runStep = () => {
    const newByteWords = quineSystem.step();
    setByteWords([...newByteWords]);
  };

  const resetSimulation = () => {
    const system = new QuineSystem(initialByteWords);
    setQuineSystem(system);
    setByteWords([...initialByteWords]);
    setAutoPlay(false);
  };

  const handleEditByteWord = (index) => {
    setEditIndex(index === editIndex ? null : index);
  };

  const updateByteWord = (newByteWord) => {
    if (editIndex === null) return;
    
    const newByteWords = [...byteWords];
    newByteWords[editIndex] = newByteWord;
    setByteWords(newByteWords);
    
    // Reset the simulation with updated ByteWords
    setQuineSystem(new QuineSystem(newByteWords));
  };

  const handleByteWordHover = (index) => {
    setHighlightIndex(index);
  };

  const handleByteWordLeave = () => {
    setHighlightIndex(null);
  };

  const renderSystemState = () => {
    if (displayMode === 'visual') {
      return (
        <div>
          <div className="flex flex-wrap justify-center mt-4">
            {byteWords.map((bw, idx) => (
              <div 
                key={idx} 
                className="relative"
                onClick={() => handleEditByteWord(idx)}
                onMouseEnter={() => handleByteWordHover(idx)}
                onMouseLeave={handleByteWordLeave}
              >
                <ByteWordDisplay 
                  byteWord={bw} 
                  index={idx} 
                  highlightColor={editIndex === idx ? '#f0f8ff' : (highlightIndex === idx ? '#e0e0e0' : null)}
                />
              </div>
            ))}
          </div>
          {editIndex !== null && (
            <div className="mt-4 max-w-md mx-auto">
              <h3 className="text-lg font-semibold mb-2">Edit ByteWord {String.fromCharCode(65 + editIndex)}</h3>
              <ByteWordEditor byteWord={byteWords[editIndex]} onChange={updateByteWord} />
            </div>
          )}
        </div>
      );
    } else {
      return (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-300">
            <thead>
              <tr>
                <th className="py-2 px-4 border-b">ID</th>
                <th className="py-2 px-4 border-b">Binary</th>
                <th className="py-2 px-4 border-b">Value</th>
                <th className="py-2 px-4 border-b">T (State)</th>
                <th className="py-2 px-4 border-b">V (Morphism)</th>
                <th className="py-2 px-4 border-b">C (Control)</th>
                <th className="py-2 px-4 border-b">Function</th>
                <th className="py-2 px-4 border-b">Actions</th>
              </tr>
            </thead>
            <tbody>
              {byteWords.map((bw, idx) => (
                <tr key={idx} className={editIndex === idx ? 'bg-blue-50' : ''}>
                  <td className="py-2 px-4 border-b">{String.fromCharCode(65 + idx)}</td>
                  <td className="py-2 px-4 border-b font-mono">{bw.toString()}</td>
                  <td className="py-2 px-4 border-b">{bw.value} ({bw.toHex()})</td>
                  <td className="py-2 px-4 border-b">{bw.state_data}</td>
                  <td className="py-2 px-4 border-b">{bw.morphism}</td>
                  <td className="py-2 px-4 border-b">{bw.floor_morphic}</td>
                  <td className="py-2 px-4 border-b">{getMorphismDescription(bw.morphism)}</td>
                  <td className="py-2 px-4 border-b">
                    <button 
                      className="bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600"
                      onClick={() => handleEditByteWord(idx)}
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
  };

  const renderReplicationHistory = () => {
    if (!showReplicationHistory) return null;
    
    return (
      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-2">Replication History</h3>
        <div className="bg-gray-100 p-4 rounded overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr>
                <th className="py-2 px-4 border-b">Step</th>
                <th className="py-2 px-4 border-b">ByteWord Count</th>
                <th className="py-2 px-4 border-b">ByteWord Values</th>
              </tr>
            </thead>
            <tbody>
              {quineSystem.replicationHistory.map((state, step) => (
                <tr key={step} className={step === quineSystem.currentStep ? 'bg-yellow-100' : ''}>
                  <td className="py-2 px-4 border-b">{step}</td>
                  <td className="py-2 px-4 border-b">{state.length}</td>
                  <td className="py-2 px-4 border-b font-mono">
                    {state.map((value, i) => (
                      <span key={i} className="mr-2">
                        {String.fromCharCode(65 + i)}:{value.toString(16).padStart(2, '0')}
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold text-center mb-4">ByteWord Self-Replicating Pattern Playground</h1>
      
      <div className="bg-gray-100 p-4 rounded mb-6">
        <h2 className="text-lg font-semibold mb-2">ByteWord Structure</h2>
        <p className="font-mono text-center">T T T T | V V V C</p>
        <p className="text-sm text-gray-600 mt-1">
          where: T=state/data (4 bits), V=morphism selector (3 bits), C=control bit (1 bit)
        </p>
      </div>
      
      <div className="flex justify-between mb-4 flex-wrap">
        <div>
          <button 
            className="bg-blue-500 text-white px-4 py-2 rounded mr-2 hover:bg-blue-600"
            onClick={runStep}
          >
            Step
          </button>
          <button 
            className={`px-4 py-2 rounded mr-2 ${autoPlay ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-green-500 hover:bg-green-600 text-white'}`}
            onClick={() => setAutoPlay(!autoPlay)}
          >
            {autoPlay ? 'Pause' : 'Auto Play'}
          </button>
          <button 
            className="bg-gray-500 text-white px-4 py-2 rounded mr-2 hover:bg-gray-600"
            onClick={resetSimulation}
          >
            Reset
          </button>
        </div>
        
        <div className="flex items-center">
          <label className="mr-2">Speed:</label>
          <input 
            type="range" 
            min="100" 
            max="2000" 
            step="100" 
            value={speed} 
            onChange={(e) => setSpeed(parseInt(e.target.value))} 
            className="mr-2"
          />
          <span>{speed}ms</span>
        </div>
        
        <div>
          <button 
            className={`px-4 py-2 rounded mr-2 ${displayMode === 'visual' ? 'bg-blue-500 text-white' : 'bg-gray-300'}`}
            onClick={() => setDisplayMode('visual')}
          >
            Visual
          </button>
          <button 
            className={`px-4 py-2 rounded mr-2 ${displayMode === 'table' ? 'bg-blue-500 text-white' : 'bg-gray-300'}`}
            onClick={() => setDisplayMode('table')}
          >
            Table
          </button>
          <button 
            className={`px-4 py-2 rounded ${showReplicationHistory ? 'bg-blue-500 text-white' : 'bg-gray-300'}`}
            onClick={() => setShowReplicationHistory(!showReplicationHistory)}
          >
            {showReplicationHistory ? 'Hide History' : 'Show History'}
          </button>
        </div>
      </div>
      
      <div className="py-2 text-center bg-blue-50 rounded mb-4">
        <span className="font-semibold">Current Step:</span> {quineSystem.currentStep} | 
        <span className="font-semibold ml-4">ByteWord Count:</span> {byteWords.length}
      </div>
      
      {renderSystemState()}
      {renderReplicationHistory()}
      
      <div className="mt-8 bg-gray-50 p-4 rounded">
        <h3 className="text-lg font-semibold mb-2">About This Playground</h3>
        <p className="text-sm mb-2">
          This playground simulates ByteWord self-replicating patterns based on morphological transformations. Each ByteWord contains:
        </p>
        <ul className="text-sm list-disc pl-5 mb-2">
          <li>A state/data field (T) - 4 bits that store the current state or value</li>
          <li>A morphism selector (V) - 3 bits that determine what transformation to apply</li>
          <li>A control bit (C) - 1 bit that affects pointability and transformation behavior</li>
        </ul>
        <p className="text-sm">
          The system demonstrates computational morphology, where ByteWords can interact, transform each other, and even replicate to form new patterns based on their encoded rules.
        </p>
      </div>
    </div>
  );
};

export default ByteWordPlayground;