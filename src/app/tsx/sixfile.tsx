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
          style={{ width: '100%', padding: '4px'}},
          value={floorMorphic}
          onChange={handleFloorMorphicChange}
          style={{ width: '100%', padding: '4px', border: '1px solid #ccc', borderRadius: '4px' }}
        >
          <option value="0">0 - Static</option>
          <option value="1">1 - Dynamic</option>
        </select>
      </div>
      <div style={{ marginTop: '10px', textAlign: 'center' }}>
        <div style={{ fontFamily: 'monospace', fontSize: '16px' }}>
          Binary: {byteWord.toString()}
        </div>
        <div style={{ fontFamily: 'monospace', fontSize: '16px' }}>
          Hex: {byteWord.toHex()}
        </div>
      </div>
    </div>
  );
};

const ReplicationHistoryChart = ({ history, maxDisplayed = 15 }) => {
  // Calculate which history entries to display if we have more than maxDisplayed
  const displayHistory = history.length <= maxDisplayed 
    ? history 
    : history.slice(history.length - maxDisplayed);
  
  const maxCount = Math.max(...displayHistory.map(entry => entry.length));
  const chartHeight = 200;
  const barWidth = `${90 / displayHistory.length}%`;
  
  return (
    <div style={{ 
      width: '100%', 
      height: `${chartHeight + 50}px`, 
      border: '1px solid #ddd',
      borderRadius: '5px',
      padding: '10px',
      marginTop: '20px'
    }}>
      <h3 style={{ textAlign: 'center', margin: '0 0 10px 0' }}>Replication History</h3>
      <div style={{ display: 'flex', height: `${chartHeight}px`, alignItems: 'flex-end', justifyContent: 'space-around' }}>
        {displayHistory.map((entry, index) => (
          <div key={index} style={{
            height: `${(entry.length / maxCount) * chartHeight}px`,
            width: barWidth,
            backgroundColor: '#0066cc',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-start',
            alignItems: 'center',
            color: 'white',
            position: 'relative'
          }}>
            <div style={{ 
              position: 'absolute',
              top: '-25px',
              fontSize: '12px',
              color: 'black'
            }}>
              {entry.length}
            </div>
            <div style={{ 
              position: 'absolute',
              bottom: '-25px',
              fontSize: '12px',
              color: 'black'
            }}>
              {history.length <= maxDisplayed 
                ? `Step ${index}` 
                : `Step ${history.length - displayHistory.length + index}`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const EntropyChart = ({ entropyHistory }) => {
  const maxEntropy = Math.max(...entropyHistory, 3); // Set minimum y-axis to 3 for better visualization
  const chartHeight = 200;
  const barWidth = `${90 / entropyHistory.length}%`;
  
  return (
    <div style={{ 
      width: '100%', 
      height: `${chartHeight + 50}px`, 
      border: '1px solid #ddd',
      borderRadius: '5px',
      padding: '10px',
      marginTop: '20px'
    }}>
      <h3 style={{ textAlign: 'center', margin: '0 0 10px 0' }}>System Entropy</h3>
      <div style={{ display: 'flex', height: `${chartHeight}px`, alignItems: 'flex-end', justifyContent: 'space-around' }}>
        {entropyHistory.map((entropy, index) => (
          <div key={index} style={{
            height: `${(entropy / maxEntropy) * chartHeight}px`,
            width: barWidth,
            backgroundColor: '#4CAF50',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-start',
            alignItems: 'center',
            color: 'white',
            position: 'relative'
          }}>
            <div style={{ 
              position: 'absolute',
              top: '-25px',
              fontSize: '12px',
              color: 'black'
            }}>
              {entropy.toFixed(2)}
            </div>
            <div style={{ 
              position: 'absolute',
              bottom: '-25px',
              fontSize: '12px',
              color: 'black'
            }}>
              {`Step ${index}`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const ByteWordSimulator = () => {
  const [byteWords, setByteWords] = useState([
    new ByteWord(0x29), // 0010|1001 - Copy Transform
    new ByteWord(0x35), // 0011|0101 - Swap Nibbles Transform
    new ByteWord(0x11)  // 0001|0001 - Copy Transform with C=1
  ]);
  const [quineSystem, setQuineSystem] = useState(() => new QuineSystem(byteWords, 50));
  const [selectedByteWordIndex, setSelectedByteWordIndex] = useState(null);
  const [runningSimulation, setRunningSimulation] = useState(false);
  const [simulationSpeed, setSimulationSpeed] = useState(500); // ms between steps
  const [entropyHistory, setEntropyHistory] = useState([quineSystem.getEntropy()]);
  const [transformationArrows, setTransformationArrows] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  useEffect(() => {
    let intervalId;
    
    if (runningSimulation) {
      intervalId = setInterval(() => {
        stepSimulation();
      }, simulationSpeed);
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [runningSimulation, simulationSpeed, quineSystem]);
  
  const stepSimulation = () => {
    setQuineSystem(prevSystem => {
      const updatedSystem = new QuineSystem(prevSystem.byteWords, 50);
      updatedSystem.currentStep = prevSystem.currentStep;
      updatedSystem.replicationHistory = [...prevSystem.replicationHistory];
      
      updatedSystem.step();
      setByteWords([...updatedSystem.byteWords]);
      setEntropyHistory(prev => [...prev, updatedSystem.getEntropy()]);
      
      // Stop simulation if we reach the maximum allowed size
      if (updatedSystem.byteWords.length >= updatedSystem.maxSize) {
        setRunningSimulation(false);
      }
      
      return updatedSystem;
    });
  };
  
  const resetSimulation = () => {
    setRunningSimulation(false);
    const initialByteWords = [
      new ByteWord(0x29),
      new ByteWord(0x35),
      new ByteWord(0x11)
    ];
    setByteWords(initialByteWords);
    setQuineSystem(new QuineSystem(initialByteWords, 50));
    setEntropyHistory([new QuineSystem(initialByteWords, 50).getEntropy()]);
    setSelectedByteWordIndex(null);
  };
  
  const handleByteWordChange = (index, newByteWord) => {
    const newByteWords = [...byteWords];
    newByteWords[index] = newByteWord;
    setByteWords(newByteWords);
    
    // Update quine system with new ByteWords
    const updatedSystem = new QuineSystem(newByteWords, 50);
    updatedSystem.currentStep = quineSystem.currentStep;
    updatedSystem.replicationHistory = [...quineSystem.replicationHistory];
    setQuineSystem(updatedSystem);
    
    // Update entropy history
    const lastEntropy = updatedSystem.getEntropy();
    setEntropyHistory(prev => [...prev.slice(0, -1), lastEntropy]);
  };
  
  const addNewByteWord = () => {
    // Add a new random ByteWord
    const newByteWord = new ByteWord(Math.floor(Math.random() * 256));
    const newByteWords = [...byteWords, newByteWord];
    setByteWords(newByteWords);
    
    // Update quine system with new ByteWords
    const updatedSystem = new QuineSystem(newByteWords, 50);
    updatedSystem.currentStep = quineSystem.currentStep;
    updatedSystem.replicationHistory = [...quineSystem.replicationHistory];
    setQuineSystem(updatedSystem);
    
    // Update entropy history
    const lastEntropy = updatedSystem.getEntropy();
    setEntropyHistory(prev => [...prev.slice(0, -1), lastEntropy]);
  };

  const removeByteWord = (index) => {
    if (byteWords.length <= 1) return; // Prevent removing the last ByteWord
    
    const newByteWords = byteWords.filter((_, i) => i !== index);
    setByteWords(newByteWords);
    
    // Update quine system with new ByteWords
    const updatedSystem = new QuineSystem(newByteWords, 50);
    updatedSystem.currentStep = quineSystem.currentStep;
    updatedSystem.replicationHistory = [...quineSystem.replicationHistory];
    setQuineSystem(updatedSystem);
    
    // Update entropy history
    const lastEntropy = updatedSystem.getEntropy();
    setEntropyHistory(prev => [...prev.slice(0, -1), lastEntropy]);
    
    if (selectedByteWordIndex === index) {
      setSelectedByteWordIndex(null);
    } else if (selectedByteWordIndex > index) {
      setSelectedByteWordIndex(selectedByteWordIndex - 1);
    }
  };
  
  const handleByteWordHover = (index) => {
    // Show transformation arrows when hovering over a ByteWord
    const current = byteWords[index];
    const targetIndex = (index + 1) % byteWords.length;
    
    setTransformationArrows([{
      from: index,
      to: targetIndex,
      type: current.morphism
    }]);
  };
  
  const handleByteWordLeave = () => {
    setTransformationArrows([]);
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px' }}>
      <h1 style={{ textAlign: 'center' }}>Self-Replicating ByteWords System</h1>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div>
          <button 
            onClick={() => setRunningSimulation(!runningSimulation)}
            style={{
              padding: '8px 16px',
              margin: '5px',
              backgroundColor: runningSimulation ? '#cc0000' : '#00cc66',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {runningSimulation ? 'Pause Simulation' : 'Run Simulation'}
          </button>
          <button 
            onClick={stepSimulation}
            disabled={runningSimulation}
            style={{
              padding: '8px 16px',
              margin: '5px',
              backgroundColor: runningSimulation ? '#ccc' : '#0066cc',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: runningSimulation ? 'not-allowed' : 'pointer'
            }}
          >
            Step
          </button>
          <button 
            onClick={resetSimulation}
            style={{
              padding: '8px 16px',
              margin: '5px',
              backgroundColor: '#ff9900',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Reset
          </button>
        </div>
        <div>
          <label style={{ marginRight: '10px' }}>
            Simulation Speed:
            <input
              type="range"
              min="100"
              max="2000"
              step="100"
              value={simulationSpeed}
              onChange={(e) => setSimulationSpeed(parseInt(e.target.value))}
              style={{ marginLeft: '10px' }}
            />
            {simulationSpeed}ms
          </label>
        </div>
      </div>
      
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        margin: '20px 0'
      }}>
        <h2>Current System State (Step {quineSystem.currentStep})</h2>
        <div style={{ 
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'flex-start',
          position: 'relative'
        }}>
          {byteWords.map((byteWord, index) => (
            <div key={index} style={{ position: 'relative' }}>
              <ByteWordDisplay
                byteWord={byteWord}
                index={index}
                highlightColor={selectedByteWordIndex === index ? '#e6f7ff' : null}
                onClick={() => setSelectedByteWordIndex(index === selectedByteWordIndex ? null : index)}
                onHover={() => handleByteWordHover(index)}
                onLeave={handleByteWordLeave}
              />
              <button
                onClick={() => removeByteWord(index)}
                style={{
                  position: 'absolute',
                  top: '-15px',
                  right: '-15px',
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  backgroundColor: '#ff0000',
                  color: 'white',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  fontSize: '12px'
                }}
              >
                ×
              </button>
            </div>
          ))}
          <button
            onClick={addNewByteWord}
            style={{
              margin: '5px',
              padding: '8px 16px',
              backgroundColor: '#00cc66',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              height: '40px',
              alignSelf: 'center'
            }}
          >
            + Add ByteWord
          </button>
        </div>
      </div>
      
      {/* ByteWord Editor */}
      {selectedByteWordIndex !== null && (
        <div style={{
          padding: '15px',
          border: '1px solid #ccc',
          borderRadius: '8px',
          backgroundColor: '#f9f9f9',
          marginTop: '20px'
        }}>
          <h3>Edit ByteWord {String.fromCharCode(65 + selectedByteWordIndex)}</h3>
          <ByteWordEditor
            byteWord={byteWords[selectedByteWordIndex]}
            onChange={(newByteWord) => handleByteWordChange(selectedByteWordIndex, newByteWord)}
          />
        </div>
      )}
      
      <button 
        onClick={() => setShowAdvanced(!showAdvanced)}
        style={{
          padding: '8px 16px',
          margin: '20px 0',
          backgroundColor: '#666',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        {showAdvanced ? 'Hide Advanced Analytics' : 'Show Advanced Analytics'}
      </button>
      
      {showAdvanced && (
        <div>
          {/* System Stats */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            padding: '10px',
            backgroundColor: '#f5f5f5',
            borderRadius: '5px',
            marginBottom: '20px'
          }}>
            <div>
              <strong>ByteWords Count:</strong> {byteWords.length}
            </div>
            <div>
              <strong>System Entropy:</strong> {quineSystem.getEntropy().toFixed(3)}
            </div>
            <div>
              <strong>Morphism Distribution:</strong> {
                Array(8).fill(0).map((_, i) => 
                  byteWords.filter(bw => bw.morphism === i).length
                ).join(', ')
              }
            </div>
          </div>
          
          {/* Charts */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <ReplicationHistoryChart history={quineSystem.replicationHistory} />
            <EntropyChart entropyHistory={entropyHistory} />
          </div>
        </div>
      )}
      
      <div style={{ marginTop: '30px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
        <h3>About ByteWord System</h3>
        <p>This simulator demonstrates a self-replicating system of ByteWords, each containing an 8-bit value with special semantics:</p>
        <ul>
          <li><strong>T (State Data):</strong> 4 high bits representing the state information</li>
          <li><strong>V (Morphism):</strong> 3 middle bits that determine how the ByteWord transforms others</li>
          <li><strong>C (Control Bit):</strong> 1 least significant bit determining behavior modes</li>
        </ul>
        <p>Each ByteWord has a transformation behavior determined by its morphism value:</p>
        <ul>
          <li><strong>0:</strong> Identity - No change to target</li>
          <li><strong>1:</strong> Copy - Creates a replication of target</li>
          <li><strong>2:</strong> Increment - Increases target's value</li>
          <li><strong>3:</strong> XNOR Transform - Applies logical XNOR operation</li>
          <li><strong>4:</strong> Toggle Control - Flips target's control bit</li>
          <li><strong>5:</strong> Swap Nibbles - Exchanges high and low nibbles</li>
          <li><strong>6:</strong> Bitwise NOT - Inverts all bits</li>
          <li><strong>7:</strong> Random - Randomizes target's value</li>
        </ul>
        <p>The system evolves as each ByteWord applies its transformation to the next ByteWord in sequence. Copy transforms (V=1) add new ByteWords to the system, allowing it to grow.</p>
      </div>
    </div>
  );
};

// Main App Component
const App = () => {
  return (
    <div style={{ fontFamily: 'Arial, sans-serif' }}>
      <ByteWordSimulator />
    </div>
  );
};

export default App;