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
          style={{ width: '100%', padding: '4px'}
    </div>

<div>
  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
    Floor Morphic/Control Bit (C - 1 bit):
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
<div style={{ marginTop: '12px', fontSize: '13px', textAlign: 'center' }}>
  Resulting Value: {byteWord.toHex()} ({byteWord.value})
</div>
</div>
);
};

// The main visualization and control component for the QuineSystem
const QuineSystemVisualizer = () => {
// Initial ByteWords - a mix of different morphisms for interesting behavior
const initialByteWords = [
new ByteWord(0x23), // T=2, V=1, C=1 (Copy transform)
new ByteWord(0x61), // T=6, V=0, C=1 (Identity transform)
new ByteWord(0x37)  // T=3, V=3, C=1 (XNOR transform)
];

const [system, setSystem] = useState(new QuineSystem(initialByteWords, 50)); // Limit to 50 ByteWords
const [selectedByteWord, setSelectedByteWord] = useState(null);
const [selectedIndex, setSelectedIndex] = useState(null);
const [isAutoPlaying, setIsAutoPlaying] = useState(false);
const [playbackSpeed, setPlaybackSpeed] = useState(1000); // 1 second
const [showConnectionLines, setShowConnectionLines] = useState(true);
const [hoverIndex, setHoverIndex] = useState(null);
const [entropy, setEntropy] = useState(system.getEntropy());

const canvasRef = React.useRef(null);

// Auto-play timer
useEffect(() => {
let timer;
if (isAutoPlaying) {
timer = setInterval(() => {
  stepSimulation();
}, playbackSpeed);
}
return () => {
if (timer) clearInterval(timer);
};
}, [isAutoPlaying, playbackSpeed, system]);

// Draw connection lines on canvas
useEffect(() => {
if (!canvasRef.current || !showConnectionLines) return;

const canvas = canvasRef.current;
const ctx = canvas.getContext('2d');
ctx.clearRect(0, 0, canvas.width, canvas.height);

if (system.byteWords.length <= 1) return;

// Get all byteword elements
const byteWordElements = document.querySelectorAll('[data-byteword-index]');
if (byteWordElements.length <= 1) return;

// Draw connections
ctx.beginPath();
ctx.strokeStyle = 'rgba(0, 102, 204, 0.5)';
ctx.lineWidth = 2;

byteWordElements.forEach((el, idx) => {
const sourceRect = el.getBoundingClientRect();
const sourceX = sourceRect.left + sourceRect.width / 2;
const sourceY = sourceRect.top + sourceRect.height / 2;

// Get target element (next in sequence)
const targetIdx = (idx + 1) % byteWordElements.length;
const targetEl = byteWordElements[targetIdx];
const targetRect = targetEl.getBoundingClientRect();
const targetX = targetRect.left + targetRect.width / 2;
const targetY = targetRect.top + targetRect.height / 2;

// Adjust coordinates to be relative to canvas
const canvasRect = canvas.getBoundingClientRect();
const adjSourceX = sourceX - canvasRect.left;
const adjSourceY = sourceY - canvasRect.top;
const adjTargetX = targetX - canvasRect.left;
const adjTargetY = targetY - canvasRect.top;

// Draw arrow
ctx.moveTo(adjSourceX, adjSourceY);
ctx.lineTo(adjTargetX, adjTargetY);

// Draw arrowhead
const angle = Math.atan2(adjTargetY - adjSourceY, adjTargetX - adjSourceX);
const arrowSize = 8;
ctx.lineTo(
  adjTargetX - arrowSize * Math.cos(angle - Math.PI/6),
  adjTargetY - arrowSize * Math.sin(angle - Math.PI/6)
);
ctx.moveTo(adjTargetX, adjTargetY);
ctx.lineTo(
  adjTargetX - arrowSize * Math.cos(angle + Math.PI/6),
  adjTargetY - arrowSize * Math.sin(angle + Math.PI/6)
);
});

ctx.stroke();
}, [system.byteWords, showConnectionLines, canvasRef.current]);

// Update canvas size when window resizes
useEffect(() => {
const handleResize = () => {
if (canvasRef.current) {
  const container = canvasRef.current.parentElement;
  canvasRef.current.width = container.clientWidth;
  canvasRef.current.height = container.clientHeight;
  // Redraw connections
  const event = new Event('resize');
  window.dispatchEvent(event);
}
};

window.addEventListener('resize', handleResize);
// Initial size setup
setTimeout(handleResize, 100);

return () => {
window.removeEventListener('resize', handleResize);
};
}, []);

const stepSimulation = () => {
const newSystem = new QuineSystem([...system.byteWords], 50);
newSystem.replicationHistory = [...system.replicationHistory];
newSystem.currentStep = system.currentStep;
newSystem.step();
setSystem(newSystem);
setEntropy(newSystem.getEntropy());
setSelectedByteWord(null);
setSelectedIndex(null);
};

const resetSimulation = () => {
setSystem(new QuineSystem(initialByteWords, 50));
setEntropy(system.getEntropy());
setSelectedByteWord(null);
setSelectedIndex(null);
setIsAutoPlaying(false);
};

const handleByteWordClick = (byteWord, index) => {
setSelectedByteWord(byteWord);
setSelectedIndex(index);
};

const handleByteWordUpdate = (updatedByteWord) => {
if (selectedIndex === null) return;

const newByteWords = [...system.byteWords];
newByteWords[selectedIndex] = updatedByteWord;

const newSystem = new QuineSystem(newByteWords, 50);
newSystem.replicationHistory = [...system.replicationHistory];
newSystem.currentStep = system.currentStep;
setSystem(newSystem);
setEntropy(newSystem.getEntropy());
setSelectedByteWord(updatedByteWord);
};

const toggleAutoPlay = () => {
setIsAutoPlaying(!isAutoPlaying);
};

const handleSpeedChange = (e) => {
setPlaybackSpeed(parseInt(e.target.value, 10));
};

const handleAddRandomByteWord = () => {
if (system.byteWords.length >= 50) return; // Respect max size

const randomValue = Math.floor(Math.random() * 256);
const newByteWords = [...system.byteWords, new ByteWord(randomValue)];

const newSystem = new QuineSystem(newByteWords, 50);
newSystem.replicationHistory = [...system.replicationHistory];
newSystem.currentStep = system.currentStep;
setSystem(newSystem);
setEntropy(newSystem.getEntropy());
};

const handleRemoveByteWord = (index) => {
if (system.byteWords.length <= 1) return; // Keep at least one ByteWord

const newByteWords = [...system.byteWords];
newByteWords.splice(index, 1);

const newSystem = new QuineSystem(newByteWords, 50);
newSystem.replicationHistory = [...system.replicationHistory];
newSystem.currentStep = system.currentStep;
setSystem(newSystem);
setEntropy(newSystem.getEntropy());

if (selectedIndex === index) {
setSelectedByteWord(null);
setSelectedIndex(null);
} else if (selectedIndex > index) {
setSelectedIndex(selectedIndex - 1);
}
};

const getColorForByteWord = (byteWord, index) => {
if (index === selectedIndex) {
return '#e6f7ff'; // Light blue for selected
} else if (byteWord.morphism === 1) {
return '#f0f9eb'; // Light green for copy transform
} else if (byteWord.morphism === 3) {
return '#fff1f0'; // Light red for XNOR transform
} else if (byteWord.morphism === 7) {
return '#f9f0ff'; // Light purple for random transform
}
return null; // Default color
};

return (
<div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px' }}>
<h1 style={{ textAlign: 'center', marginBottom: '20px' }}>Self-Replicating ByteWord System</h1>

<div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
  <div>
    <button 
      onClick={stepSimulation}
      disabled={isAutoPlaying}
      style={{ 
        padding: '8px 16px', 
        backgroundColor: '#0066cc', 
        color: 'white', 
        border: 'none', 
        borderRadius: '4px',
        marginRight: '10px',
        cursor: isAutoPlaying ? 'not-allowed' : 'pointer'
      }}
    >
      Step Forward
    </button>
    
    <button 
      onClick={toggleAutoPlay}
      style={{ 
        padding: '8px 16px', 
        backgroundColor: isAutoPlaying ? '#cc0000' : '#00cc66', 
        color: 'white', 
        border: 'none', 
        borderRadius: '4px',
        marginRight: '10px'
      }}
    >
      {isAutoPlaying ? 'Stop' : 'Auto-Play'}
    </button>
    
    <button 
      onClick={resetSimulation}
      style={{ 
        padding: '8px 16px', 
        backgroundColor: '#666666', 
        color: 'white', 
        border: 'none', 
        borderRadius: '4px',
        marginRight: '10px'
      }}
    >
      Reset
    </button>
    
    <button 
      onClick={handleAddRandomByteWord}
      disabled={system.byteWords.length >= 50}
      style={{ 
        padding: '8px 16px', 
        backgroundColor: system.byteWords.length >= 50 ? '#cccccc' : '#6600cc', 
        color: 'white', 
        border: 'none', 
        borderRadius: '4px',
        cursor: system.byteWords.length >= 50 ? 'not-allowed' : 'pointer'
      }}
    >
      Add Random ByteWord
    </button>
  </div>
  
  <div>
    <label style={{ marginRight: '10px' }}>
      <input 
        type="checkbox" 
        checked={showConnectionLines}
        onChange={() => setShowConnectionLines(!showConnectionLines)}
      />
      Show Connections
    </label>
    
    <label>
      Speed: 
      <select value={playbackSpeed} onChange={handleSpeedChange} style={{ marginLeft: '5px' }}>
        <option value="2000">Slow</option>
        <option value="1000">Normal</option>
        <option value="500">Fast</option>
        <option value="200">Very Fast</option>
      </select>
    </label>
  </div>
</div>

<div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between' }}>
  <div>
    <span style={{ fontWeight: 'bold' }}>Current Step: {system.currentStep}</span>
    <span style={{ marginLeft: '20px', fontWeight: 'bold' }}>
      ByteWords: {system.byteWords.length}
    </span>
    <span style={{ marginLeft: '20px', fontWeight: 'bold' }}>
      Entropy: {entropy.toFixed(2)}
    </span>
  </div>
</div>

<div style={{ position: 'relative', height: '300px', border: '1px solid #ccc', borderRadius: '4px', marginBottom: '20px', overflow: 'auto' }}>
  <canvas 
    ref={canvasRef} 
    style={{ 
      position: 'absolute', 
      top: 0, 
      left: 0, 
      width: '100%', 
      height: '100%', 
      pointerEvents: 'none', 
      zIndex: 1 
    }} 
  />
  <div style={{ padding: '20px', display: 'flex', flexWrap: 'wrap', zIndex: 2, position: 'relative' }}>
    {system.byteWords.map((byteWord, index) => (
      <div key={`${byteWord.value}-${index}`} data-byteword-index={index}>
        <div style={{ position: 'relative' }}>
          {hoverIndex === index && (
            <button
              onClick={() => handleRemoveByteWord(index)}
              style={{
                position: 'absolute',
                top: '-10px',
                right: '-10px',
                backgroundColor: '#cc0000',
                color: 'white',
                border: 'none',
                borderRadius: '50%',
                width: '20px',
                height: '20px',
                cursor: 'pointer',
                zIndex: 3
              }}
            >
              ×
            </button>
          )}
          <ByteWordDisplay
            byteWord={byteWord}
            index={index}
            highlightColor={getColorForByteWord(byteWord, index)}
            onClick={() => handleByteWordClick(byteWord, index)}
            onHover={() => setHoverIndex(index)}
            onLeave={() => setHoverIndex(null)}
          />
        </div>
      </div>
    ))}
  </div>
</div>

{selectedByteWord && (
  <div style={{ 
    border: '1px solid #0066cc', 
    borderRadius: '5px', 
    padding: '15px', 
    backgroundColor: '#f0f8ff'
  }}>
    <h3>Edit ByteWord {String.fromCharCode(65 + selectedIndex)}</h3>
    <ByteWordEditor
      byteWord={selectedByteWord}
      onChange={handleByteWordUpdate}
    />
  </div>
)}

<div style={{ marginTop: '30px' }}>
  <h3>System Information</h3>
  <p>
    This is a self-replicating system of ByteWords that can transform and copy each other.
    Each ByteWord consists of three parts:
  </p>
  <ul>
    <li><strong>T (State Data)</strong>: 4 bits that represent the ByteWord's state</li>
    <li><strong>V (Morphism)</strong>: 3 bits that determine how this ByteWord transforms others</li>
    <li><strong>C (Control Bit)</strong>: 1 bit that can modify the transformation behavior</li>
  </ul>
  <p>
    Morphism types:
  </p>
  <ul>
    <li><strong>0: Identity</strong> - No change to target</li>
    <li><strong>1: Copy</strong> - Creates a copy of target</li>
    <li><strong>2: Increment</strong> - Increments target's value</li>
    <li><strong>3: XNOR</strong> - Performs XNOR on target's state data</li>
    <li><strong>4: Toggle Control</strong> - Toggles target's control bit</li>
    <li><strong>5: Swap Nibbles</strong> - Swaps target's high and low nibbles</li>
    <li><strong>6: Bitwise NOT</strong> - Inverts all bits in target</li>
    <li><strong>7: Random</strong> - Transforms target to random value</li>
  </ul>
  <p>
    Click on a ByteWord to edit its properties. Watch the system evolve as ByteWords interact and replicate.
  </p>
</div>
</div>
);
};

// Main App component
const App = () => {
return (
<div style={{ fontFamily: 'Arial, sans-serif' }}>
<QuineSystemVisualizer />
</div>
);
};

// Render the application
const rootElement = document.getElementById('root');
if (rootElement) {
const root = ReactDOM.createRoot(rootElement);
root.render(<App />);
} else {
console.error("Root element not found");
}

// Main demo function for Node.js environments
const runDemo = () => {
console.log("ByteWord System Demonstration");
console.log("============================");

// 1. Test edge case: ByteWord with value 0 and 255
console.log("Testing edge cases for ByteWord construction:");
try {
const bwMin = new ByteWord(0);
const bwMax = new ByteWord(255);
console.log("Min value (0):", bwMin.toString(), bwMin.toHex());
console.log("Max value (255):", bwMax.toString(), bwMax.toHex());

// Test value outside range
try {
const bwOutOfRange = new ByteWord(256);
console.log("This should not be displayed");
} catch (e) {
console.log("Correctly caught out of range value:", e.message);
}
} catch (e) {
console.log("Error in edge case testing:", e.message);
}

// 2. Test fromString method for edge cases
console.log("\nTesting ByteWord.fromString edge cases:");
try {
const bwFromString = ByteWord.fromString("0010|1001");
console.log("From string:", bwFromString.toString(), bwFromString.toHex());

// Test invalid string
try {
const bwInvalidString = ByteWord.fromString("001|1001");
console.log("This should not be displayed");
} catch (e) {
console.log("Correctly caught invalid string:", e.message);
}
} catch (e) {
console.log("Error in fromString testing:", e.message);
}

// 3. Test XNOR transformation specifically
console.log("\nTesting XNOR transformation:");
try {
const bwSource = new ByteWord(0x31); // T=3, V=0, C=1
const bwTarget = new ByteWord(0x51); // T=5, V=0, C=1

console.log("Source:", bwSource.toString());
console.log("Target:", bwTarget.toString());

// Manually calculate expected XNOR result
const expectedT = ByteWord.xnor(bwTarget.state_data, bwSource.state_data);
console.log("Expected XNOR of T values:", expectedT);

// Setup source for XNOR transform (V=3)
const bwXnorSource = new ByteWord((bwSource.state_data << 4) | (3 << 1) | bwSource.floor_morphic);
console.log("XNOR source:", bwXnorSource.toString());

const result = bwXnorSource.transform(bwTarget);
console.log("XNOR transform result:", result.toString());

// Verify result matches our expected value
const expectedFullValue = (expectedT << 4) | (bwTarget.morphism << 1) | bwTarget.floor_morphic;
console.log("Expected full value:", expectedFullValue.toString(16));
console.log("Actual full value:", result.value.toString(16));

} catch (e) {
console.log("Error in XNOR testing:", e.message);
}

// 4. Test QuineSystem with different initial conditions
console.log("\nTesting QuineSystem with different patterns:");

// 4.1 Create a system with mixed transforms
const mixedPattern = [
new ByteWord(0x23), // T=2, V=1, C=1 (Copy)
new ByteWord(0x61), // T=6, V=0, C=1 (Identity)
new ByteWord(0x37)  // T=3, V=3, C=1 (XNOR)
];

const mixedSystem = new QuineSystem(mixedPattern, 50);
console.log("Initial state:", mixedSystem.byteWords.map(bw => `${bw.toString()} (${getMorphismDescription(bw.morphism)})`));

// Run for 5 steps
for (let i = 0; i < 5; i++) {
mixedSystem.step();
console.log(`Step ${i+1} (${mixedSystem.byteWords.length} ByteWords)`);

// Display entropy
const entropy = mixedSystem.getEntropy();
console.log(`System entropy: ${entropy.toFixed(2)}`);

// Show sample of ByteWords if there are many
if (mixedSystem.byteWords.length > 5) {
console.log("First 5 ByteWords:", mixedSystem.byteWords.slice(0, 5).map(bw => bw.toString()));
console.log("...");
console.log("Last 2 ByteWords:", mixedSystem.byteWords.slice(-2).map(bw => bw.toString()));
} else {
console.log("All ByteWords:", mixedSystem.byteWords.map(bw => bw.toString()));
}
}

// 4.2 Create a system that oscillates
console.log("\nOscillating pattern test:");

// Create a pair of ByteWords that toggle each other's control bits
const oscillator = [
new ByteWord((2 << 4) | (4 << 1) | 0), // T=2, V=4 (Toggle Control), C=0
new ByteWord((5 << 4) | (4 << 1) | 1)  // T=5, V=4 (Toggle Control), C=1
];

const oscillatingSystem = new QuineSystem(oscillator, 10);
console.log("Initial state:", oscillatingSystem.byteWords.map(bw => bw.toString()));

// Run for 10 steps to show oscillation
for (let i = 0; i < 10; i++) {
oscillatingSystem.step();
console.log(`Step ${i+1}:`, oscillatingSystem.byteWords.map(bw => bw.toString()));
}

console.log("\nByteWord System demonstration completed.");
};

// Run demo in Node.js environment
if (typeof window === 'undefined') {
runDemo();
}

// Export classes and components for potential use in other modules
export { ByteWord, QuineSystem, getMorphismDescription, ByteWordDisplay, ByteWordEditor, QuineSystemVisualizer };