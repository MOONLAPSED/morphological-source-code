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

// Self-replicating pattern simulation with enhanced growth control
class QuineSystem {
  constructor(initialByteWords, maxSize = 100) {
    this.byteWords = [...initialByteWords];
    this.replicationHistory = [this.byteWords.map(bw => bw.value)];
    this.currentStep = 0;
    this.maxSize = maxSize;
  }

  step() {
    if (this.byteWords.length === 0) return [];
    
    // Create a copy of the current state
    const newByteWords = [...this.byteWords];
    
    // Process each ByteWord based on its morphism
    for (let i = 0; i < this.byteWords.length; i++) {
      const current = this.byteWords[i];
      const targetIndex = (i + 1) % this.byteWords.length; // Point to next ByteWord
      const target = this.byteWords[targetIndex];
      
      // Apply transformation based on the current ByteWord's morphism
      if (current.morphism === 1) { // Copy transform
        // Add a copy of the target to the end (with growth limit)
        if (newByteWords.length < this.maxSize) {
          newByteWords.push(new ByteWord(target.value));
        }
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

  reset(initialByteWords) {
    this.byteWords = [...initialByteWords];
    this.replicationHistory = [this.byteWords.map(bw => bw.value)];
    this.currentStep = 0;
  }
  
  // Get system entropy (a measure of disorder/complexity)
  getEntropy() {
    if (this.byteWords.length === 0) return 0;
    
    // Count occurrences of each unique ByteWord value
    const valueCounts = {};
    this.byteWords.forEach(bw => {
      valueCounts[bw.value] = (valueCounts[bw.value] || 0) + 1;
    });
    
    // Calculate Shannon entropy
    let entropy = 0;
    const total = this.byteWords.length;
    
    Object.values(valueCounts).forEach(count => {
      const probability = count / total;
      entropy -= probability * Math.log2(probability);
    });
    
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

const ByteWordDisplay = ({ byteWord, index, highlightColor = null, onClick, onHover, onLeave }) => {
  const style = {
    border: '2px solid #0066cc',
    borderRadius: '5px',
    padding: '8px',
    margin: '5px',
    minWidth: '120px',
    backgroundColor: highlightColor || '#fff',
    position: 'relative',
    cursor: 'pointer',
    transition: 'transform 0.2s, box-shadow 0.2s'
  };

  return (
    <div 
      style={style}
      onClick={onClick}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
    >
      <div style={{ position: 'absolute', top: '-20px', fontSize: '12px' }}>
        ByteWord {String.fromCharCode(65 + index)} ({byteWord.value})
      </div>
      <div style={{ fontFamily: 'monospace', fontSize: '16px', textAlign: 'center' }}>
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
    <div style={{
      padding: '12px',
      border: '1px solid #ccc',
      borderRadius: '4px',
      marginTop: '10px'
    }}>
      <div style={{ marginBottom: '8px' }}>
        <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
          State Data (T - 4 bits):
        </label>
        <input
          type="number"
          min="0"
          max="15"
          value={stateData}
          onChange={handleStateDataChange}
          style={{ width: '100%', padding: '4px', border: '1px solid #ccc', borderRadius: '4px' }}
        />
      </div>
      <div style={{ marginBottom: '8px' }}>
        <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
          Morphism (V - 3 bits):
        </label>
        <select
          value={morphism}
          onChange={handleMorphismChange}
          style={{ width: '100%', padding: '4px', border: '1px solid #ccc', borderRadius: '4px' }}
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
      <div style={{ marginBottom: '8px' }}>
        <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
          Control Bit (C - 1 bit):
        </label>
        <select
          value={floorMorphic}
          onChange={handleFloorMorphicChange}
          style={{ width: '100%', padding: '4px', border: '1px solid #ccc', borderRadius: '4px' }}
        >
          <option value="0">0 - Static</option>
          <option value="1">1 - Dynamic</option>
        </select>
      </div>
      <div style={{ fontSize: '12px', marginTop: '10px', padding: '4px', backgroundColor: '#f0f0f0', borderRadius: '4px' }}>
        Byte Value: {byteWord.toHex()} ({byteWord.value})
      </div>
    </div>
  );
};

// Component for visualizing the replication history
const ReplicationHistoryChart = ({ history }) => {
  // Use different colors for different ByteWord positions
  const colors = [
    '#4285F4', '#EA4335', '#FBBC05', '#34A853', 
    '#8B5CF6', '#EC4899', '#F97316', '#10B981'
  ];
  
  const maxItems = Math.max(...history.map(step => step.length));
  const stepCount = history.length;
  
  const cellSize = 20;
  const width = stepCount * cellSize;
  const height = maxItems * cellSize;
  
  return (
    <div style={{ 
      marginTop: '20px', 
      padding: '10px',
      border: '1px solid #ddd',
      borderRadius: '4px',
      overflowX: 'auto'
    }}>
      <h3 style={{ marginBottom: '10px' }}>Replication History</h3>
      <div style={{ 
        position: 'relative',
        width: `${width}px`,
        height: `${height}px`,
        backgroundColor: '#f5f5f5'
      }}>
        {history.map((step, stepIndex) => (
          step.map((value, itemIndex) => (
            <div
              key={`${stepIndex}-${itemIndex}`}
              style={{
                position: 'absolute',
                left: `${stepIndex * cellSize}px`,
                top: `${itemIndex * cellSize}px`,
                width: `${cellSize - 2}px`,
                height: `${cellSize - 2}px`,
                backgroundColor: colors[value % colors.length],
                opacity: 0.7,
                border: '1px solid rgba(0,0,0,0.2)',
                borderRadius: '3px'
              }}
              title={`Step ${stepIndex}, ByteWord ${itemIndex}: ${value}`}
            />
          ))
        ))}
      </div>
      <div style={{ marginTop: '5px', fontSize: '12px', color: '#666' }}>
        Each column represents a step, each colored cell is a ByteWord
      </div>
    </div>
  );
};

// Main application component
const QuineSystemSimulator = () => {
  const [byteWords, setByteWords] = useState([
    new ByteWord(0x29), // 0010|1001 - Copy Transform
    new ByteWord(0x35), // 0011|0101 - Swap Nibbles Transform
    new ByteWord(0x11)  // 0001|0001 - Copy Transform with C=1
  ]);
  
  const [quineSystem, setQuineSystem] = useState(new QuineSystem(byteWords));
  const [isRunning, setIsRunning] = useState(false);
  const [speed, setSpeed] = useState(500); // ms between steps
  const [selectedWordIndex, setSelectedWordIndex] = useState(-1);
  const [maxByteWords, setMaxByteWords] = useState(100);
  const [entropy, setEntropy] = useState(0);
  
  // Effect to handle auto-stepping
  useEffect(() => {
    let intervalId;
    
    if (isRunning) {
      intervalId = setInterval(() => {
        stepSimulation();
      }, speed);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isRunning, speed, quineSystem]);
  
  // Effect to update entropy when byteWords changes
  useEffect(() => {
    setEntropy(quineSystem.getEntropy());
  }, [quineSystem.byteWords]);
  
  const stepSimulation = () => {
    const updatedSystem = new QuineSystem([...quineSystem.byteWords], maxByteWords);
    updatedSystem.replicationHistory = [...quineSystem.replicationHistory];
    updatedSystem.currentStep = quineSystem.currentStep;
    updatedSystem.step();
    
    setQuineSystem(updatedSystem);
    setByteWords([...updatedSystem.byteWords]);
    setEntropy(updatedSystem.getEntropy());
  };
  
  const resetSimulation = () => {
    setIsRunning(false);
    const initialByteWords = [
      new ByteWord(0x29),
      new ByteWord(0x35),
      new ByteWord(0x11)
    ];
    setByteWords(initialByteWords);
    setQuineSystem(new QuineSystem(initialByteWords, maxByteWords));
    setSelectedWordIndex(-1);
  };
  
  const handleWordChange = (index, newByteWord) => {
    const newByteWords = [...byteWords];
    newByteWords[index] = newByteWord;
    setByteWords(newByteWords);
    
    const updatedSystem = new QuineSystem(newByteWords, maxByteWords);
    setQuineSystem(updatedSystem);
  };
  
  const addRandomByteWord = () => {
    if (byteWords.length >= maxByteWords) return;
    
    const randomValue = Math.floor(Math.random() * 256);
    const newByteWord = new ByteWord(randomValue);
    
    const newByteWords = [...byteWords, newByteWord];
    setByteWords(newByteWords);
    
    const updatedSystem = new QuineSystem(newByteWords, maxByteWords);
    setQuineSystem(updatedSystem);
  };
  
  const removeByteWord = (index) => {
    if (byteWords.length <= 1) return;
    
    const newByteWords = byteWords.filter((_, i) => i !== index);
    setByteWords(newByteWords);
    
    const updatedSystem = new QuineSystem(newByteWords, maxByteWords);
    setQuineSystem(updatedSystem);
    
    if (selectedWordIndex === index) {
      setSelectedWordIndex(-1);
    } else if (selectedWordIndex > index) {
      setSelectedWordIndex(selectedWordIndex - 1);
    }
  };
  
  const getWordHighlightColor = (index) => {
    if (index === selectedWordIndex) {
      return '#e6f7ff'; // Light blue when selected
    }
    
    const morphism = byteWords[index].morphism;
    
    // Highlight colors based on morphism type
    switch(morphism) {
      case 1: return 'rgba(144, 238, 144, 0.3)'; // Light green for Copy
      case 3: return 'rgba(255, 182, 193, 0.3)'; // Light pink for XNOR
      case 7: return 'rgba(255, 255, 224, 0.3)'; // Light yellow for Random
      default: return null;
    }
  };
  
  return (
    <div style={{ 
      fontFamily: 'Arial, sans-serif',
      margin: '20px',
      maxWidth: '1200px'
    }}>
      <h1>QuineSystem Simulator</h1>
      <p>
        A self-replicating pattern simulator based on transformative byte operations.
        Each ByteWord consists of 8 bits: 4 bits for state data (T), 3 bits for morphism type (V),
        and 1 bit for control (C).
      </p>
      
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <button 
          onClick={() => setIsRunning(!isRunning)} 
          style={{ 
            padding: '8px 16px',
            backgroundColor: isRunning ? '#f44336' : '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          {isRunning ? 'Pause' : 'Start'} Simulation
        </button>
        
        <button 
          onClick={stepSimulation}
          disabled={isRunning}
          style={{ 
            padding: '8px 16px',
            backgroundColor: isRunning ? '#ccc' : '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isRunning ? 'not-allowed' : 'pointer'
          }}
        >
          Step
        </button>
        
        <button 
          onClick={resetSimulation}
          style={{ 
            padding: '8px 16px',
            backgroundColor: '#ff9800',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Reset
        </button>
        
        <button 
          onClick={addRandomByteWord}
          disabled={byteWords.length >= maxByteWords}
          style={{ 
            padding: '8px 16px',
            backgroundColor: byteWords.length >= maxByteWords ? '#ccc' : '#9c27b0',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: byteWords.length >= maxByteWords ? 'not-allowed' : 'pointer'
          }}
        >
          Add Random ByteWord
        </button>
        
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
          <label style={{ marginRight: '10px' }}>Speed:</label>
          <input 
            type="range" 
            min="50" 
            max="2000" 
            step="50" 
            value={speed} 
            onChange={(e) => setSpeed(parseInt(e.target.value))}
            style={{ width: '100px' }}
          />
          <span style={{ marginLeft: '5px', width: '50px' }}>{speed}ms</span>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <label style={{ marginRight: '10px' }}>Max Size:</label>
          <input 
            type="number" 
            min="5" 
            max="500" 
            value={maxByteWords} 
            onChange={(e) => setMaxByteWords(parseInt(e.target.value))}
            style={{ width: '60px' }}
          />
        </div>
      </div>
      
      <div style={{ 
        display: 'flex',
        justifyContent: 'space-between',
        backgroundColor: '#f0f0f0',
        padding: '10px',
        borderRadius: '4px',
        marginBottom: '20px'
      }}>
        <div>Step: {quineSystem.currentStep}</div>
        <div>ByteWord Count: {byteWords.length} / {maxByteWords}</div>
        <div>System Entropy: {entropy.toFixed(3)}</div>
      </div>
      
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
        <div style={{ 
          flex: '2 1 600px',
          border: '1px solid #ddd',
          borderRadius: '4px',
          padding: '15px'
        }}>
          <h2>ByteWord Collection</h2>
          <div style={{ 
            display: 'flex',
            flexWrap: 'wrap',
            gap: '15px',
            maxHeight: '300px',
            overflowY: 'auto',
            padding: '10px',
            backgroundColor: '#f9f9f9',
            borderRadius: '4px'
          }}>
            {byteWords.map((byteWord, index) => (
              <div key={index} style={{ position: 'relative' }}>
                <ByteWordDisplay 
                  byteWord={byteWord} 
                  index={index}
                  highlightColor={getWordHighlightColor(index)}
                  onClick={() => setSelectedWordIndex(index === selectedWordIndex ? -1 : index)}
                />
                {byteWords.length > 1 && (
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      removeByteWord(index);
                    }}
                    style={{
                      position: 'absolute',
                      top: '-15px',
                      right: '-15px',
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      backgroundColor: '#f44336',
                      color: 'white',
                      border: 'none',
                      fontSize: '12px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
          
          <ReplicationHistoryChart history={quineSystem.replicationHistory} />
        </div>
        
        <div style={{ 
          flex: '1 1 300px',
          border: '1px solid #ddd',
          borderRadius: '4px',
          padding: '15px'
        }}>
          <h2>ByteWord Editor</h2>
          {selectedWordIndex >= 0 ? (
            <ByteWordEditor 
              byteWord={byteWords[selectedWordIndex]} 
              onChange={(newByteWord) => handleWordChange(selectedWordIndex, newByteWord)}
            />
          ) : (
            <div style={{ 
              padding: '20px',
              backgroundColor: '#f9f9f9',
              borderRadius: '4px',
              textAlign: 'center' 
            }}>
              Select a ByteWord to edit its properties
            </div>
          )}
          
          <div style={{ marginTop: '20px' }}>
            <h3>Morphism Types</h3>
            <ul style={{ fontSize: '14px' }}>
              <li><strong>Identity (0):</strong> No change to target</li>
              <li><strong>Copy (1):</strong> Creates a copy of self</li>
              <li><strong>Increment (2):</strong> Increments target value</li>
              <li><strong>XNOR (3):</strong> Applies XNOR between state data</li>
              <li><strong>Toggle Control (4):</strong> Flips target's control bit</li>
              <li><strong>Swap Nibbles (5):</strong> Swaps high and low nibbles</li>
              <li><strong>Bitwise NOT (6):</strong> Inverts all bits of target</li>
              <li><strong>Random (7):</strong> Replaces target with random value</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

// Example of running the simulation in test mode
const testByteWordSystem = () => {
  console.log("Testing ByteWord construction and transformations:");

  // Create test ByteWords
  const bw1 = new ByteWord(0x29); // 0010|1001 - Copy Transform
  const bw2 = new ByteWord(0x35); // 0011|0101 - Swap Nibbles Transform
  const bw3 = new ByteWord(0x11); // 0001|0001 - Copy Transform with C=1

  console.log("ByteWord 1:", bw1.toString(), bw1.toHex(), 
              "T:", bw1.state_data, "V:", bw1.morphism, "C:", bw1.floor_morphic);
  console.log("ByteWord 2:", bw2.toString(), bw2.toHex(), 
              "T:", bw2.state_data, "V:", bw2.morphism, "C:", bw2.floor_morphic);
  console.log("ByteWord 3:", bw3.toString(), bw3.toHex(), 
              "T:", bw3.state_data, "V:", bw3.morphism, "C:", bw3.floor_morphic);

  // Test transformations
  console.log("\nTesting transformations:");
  const transformed1 = bw1.transform(bw2);
  console.log("bw1 transforms bw2:", transformed1.toString(), transformed1.toHex());

  const transformed2 = bw2.transform(bw3);
  console.log("bw2 transforms bw3:", transformed2.toString(), transformed2.toHex());

  const transformed3 = bw3.transform(bw1);
  console.log("bw3 transforms bw1:", transformed3.toString(), transformed3.toHex());

  // Test QuineSystem
  console.log("\nTesting QuineSystem behavior:");
  const quineSystem = new QuineSystem([bw1, bw2, bw3]);

  // Run a few steps and log the results
  console.log("Initial state:", quineSystem.byteWords.map(bw => bw.toString()));

  for (let i = 0; i < 5; i++) {
    quineSystem.step();
    console.log(`Step ${i+1}:`, quineSystem.byteWords.map(bw => bw.toString()));
    console.log(`ByteWord count: ${quineSystem.byteWords.length}`);
    console.log(`System entropy: ${quineSystem.getEntropy().toFixed(3)}`);
  }

  console.log("\nReplication history:");
  console.log(quineSystem.replicationHistory);
};

// Uncomment to run the test:
// testByteWordSystem();

// Export the main component
export default QuineSystemSimulator;