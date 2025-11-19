import React, { useState, useEffect, useRef, useCallback } from 'react';

// --- Constants for Morphism Interpretation ---
const OP_MODE_VVV = 'VVV (Ops 0-7)'; // When Outer C = 1
const OP_MODE_VV = 'VV (Ops 0-3)';   // When Outer C = 0

// --- Core Logic: ByteWord Class ---
class ByteWord {
  constructor(rawValue) {
    if (rawValue < 0 || rawValue > 255 || !Number.isInteger(rawValue)) {
      console.warn(`Invalid rawValue ${rawValue} passed to ByteWord. Defaulting to 0.`);
      rawValue = 0;
    }
    this.value = rawValue & 0xFF;

    // Structure: <C _C_ VV | TTTT>
    this.outer_c = (this.value >> 7) & 0x01;       // Bit 7: Outer C (Meta/Event Horizon)
    this.dunder_c_raw = (this.value >> 6) & 0x01;  // Bit 6: The _C_ bit (raw value)
    this.core_vv = (this.value >> 4) & 0x03;       // Bits 5-4: Core VV
    this.t = this.value & 0x0F;                    // Bits 3-0: TTTT (Topology/State)

    // Determine operational mode and effective values based on outer_c
    if (this.outer_c === 1) {
      this.op_mode = OP_MODE_VVV;
      // _C_ acts as the MSB of VVV
      this.effective_morphism = (this.dunder_c_raw << 2) | this.core_vv; // VVV (0-7)
      this.internal_c = null; // Not explicitly defined in this mode
      this.is_pointable = true; // Assume active/pointable when C=1
    } else { // outer_c === 0
      this.op_mode = OP_MODE_VV;
      // _C_ acts as the internal C state
      this.effective_morphism = this.core_vv; // VV (0-3)
      this.internal_c = this.dunder_c_raw; // 0 = Anchored, 1 = Pointable (in settled state)
      this.is_pointable = (this.internal_c === 1);
    }
  }

  // --- Getters for display ---
  get outerC_bin() { return this.outer_c.toString(); }
  get dunderC_bin() { return this.dunder_c_raw.toString(); }
  get coreVV_bin() { return this.core_vv.toString(2).padStart(2, '0'); }
  get t_bin() { return this.t.toString(2).padStart(4, '0'); }

  toString() {
    return `<${this.outerC_bin} ${this.dunderC_bin} ${this.coreVV_bin} | ${this.t_bin}>`;
  }

  toHex() {
    return `0x${this.value.toString(16).padStart(2, '0')}`;
  }

  getMorphismDescription() {
    const op = this.effective_morphism;
    if (this.outer_c === 1) { // VVV Mode Descriptions (Ops 0-7)
      switch (op) {
        case 0: return "ID";
        case 1: return "Norm Inc Tgt"; // Increment target's full value
        case 2: return "Morph Inc Tgt"; // Increment target's T bits only
        case 3: return "Flip T Bits Tgt"; // Bitwise NOT on target's T bits
        case 4: return "Flip V Bits Tgt"; // Bitwise NOT on target's VVV bits (if C=1) or VV bits (if C=0)
        case 5: return "Flip C Bits Tgt"; // Flip target's Outer C and _C_
        case 6: return "Swap T Nibbles Tgt"; // Swap high/low 2 bits of T
        case 7: return "Set T Random"; // Set target T to random 4 bits
        default: return "Unknown VVV";
      }
    } else { // VV Mode Descriptions (Ops 0-3) - Reflective/Anchored Ops
      switch (op) {
        case 0: return "ID (Anchored)";
        case 1: return this.is_pointable ? "Decr T (Pointable)" : "Incr T (Anchored)"; // Op depends on _C_ state
        case 2: return "Reflect T->V"; // Copy target T bits to target VV bits (_C_ unchanged)
        case 3: return "Toggle Anchor"; // Flip target's _C_ bit (internal C)
        default: return "Unknown VV";
      }
    }
  }

  clone() {
    return new ByteWord(this.value);
  }

  // --- Transformation Logic ---
  transform(targetWord) {
    const source_op = this.effective_morphism;
    let target_val = targetWord.value;
    let target_t = targetWord.t;
    let target_vv = targetWord.core_vv;
    let target_dc = targetWord.dunder_c_raw;
    let target_oc = targetWord.outer_c;

    if (this.outer_c === 1) { // Source is Active (VVV Ops)
      switch (source_op) {
        case 0: break; // ID
        case 1: target_val = (target_val + 1) & 0xFF; break; // Norm Inc
        case 2: // Morph Inc
            target_t = (target_t + 1) & 0x0F;
            target_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
            break;
        case 3: // Flip T bits
            target_t = (~target_t) & 0x0F;
            target_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
            break;
        case 4: // Flip V bits (VV or VVV depending on target's C)
            if (target_oc === 1) { // Flip VVV (_C_VV)
                let target_vvv = (target_dc << 2) | target_vv;
                target_vvv = (~target_vvv) & 0x07;
                target_dc = (target_vvv >> 2) & 0x01;
                target_vv = target_vvv & 0x03;
            } else { // Flip VV
                target_vv = (~target_vv) & 0x03;
            }
            target_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
            break;
        case 5: // Flip C bits
            target_oc = 1 - target_oc;
            target_dc = 1 - target_dc;
            target_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
            break;
        case 6: // Swap T Nibbles
            let t_hi = (target_t >> 2) & 0x03;
            let t_lo = target_t & 0x03;
            target_t = (t_lo << 2) | t_hi;
            target_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
            break;
        case 7: // Set T Random
            target_t = Math.floor(Math.random() * 16);
            target_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
            break;
        default: break; // ID for unknown
      }
    } else { // Source is Settled (VV Ops)
      switch (source_op) {
        case 0: break; // ID (Anchored)
        case 1: // Op depends on *target's* internal C state (_C_)
            if (targetWord.is_pointable) { // Target is Pointable (_C_=1)
                target_t = (target_t - 1) & 0x0F; // Decrement T
            } else { // Target is Anchored (_C_=0)
                target_t = (target_t + 1) & 0x0F; // Increment T
            }
            target_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
            break;
        case 2: // Reflect T -> VV
            target_vv = target_t & 0x03; // Copy lower 2 bits of T to VV
            target_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
            break;
        case 3: // Toggle Anchor (_C_ bit)
            target_dc = 1 - target_dc;
            target_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
            break;
        default: break; // ID for unknown
      }
    }
    // Return a new ByteWord, ensuring value is correct
    // Need to handle case where target_val was modified directly vs reconstructed
    if (target_val !== targetWord.value) {
        return new ByteWord(target_val);
    } else {
        // If only components changed, reconstruct value to be safe
        const final_val = (target_oc << 7) | (target_dc << 6) | (target_vv << 4) | target_t;
        if (final_val !== targetWord.value) {
            return new ByteWord(final_val);
        } else {
            return targetWord.clone(); // No change occurred
        }
    }
  }
}

// --- Core Logic: QuineSystem Class ---
class QuineSystem {
  constructor(initialByteWords) {
    this.byteWords = initialByteWords.map(bw => bw instanceof ByteWord ? bw.clone() : new ByteWord(bw));
    this.currentStep = 0;
    // History only stores value arrays for stability check
    this.historyValues = [this.byteWords.map(bw => bw.value)];
  }

  step() {
    if (this.byteWords.length === 0) return false; // No change if empty

    const currentByteWords = this.byteWords;
    const nextByteWords = currentByteWords.map(bw => bw.clone());
    let changed = false;

    for (let i = 0; i < currentByteWords.length; i++) {
      const source = currentByteWords[i];
      const targetIndex = (i + 1) % currentByteWords.length;
      const target = currentByteWords[targetIndex]; // Target from *current* state

      const transformedByteWord = source.transform(target);

      if (transformedByteWord.value !== nextByteWords[targetIndex].value) {
          changed = true;
      }
      nextByteWords[targetIndex] = transformedByteWord;
    }

    this.byteWords = nextByteWords;
    this.currentStep++;
    this.historyValues.push(this.byteWords.map(bw => bw.value));
    return changed; // Return true if any word changed value
  }

  getStateHash() {
    // Simple hash based on joining values - good enough for stability check
    return this.byteWords.map(bw => bw.value).join(',');
  }

  reset(initialByteWords) {
    this.byteWords = initialByteWords.map(bw => bw instanceof ByteWord ? bw.clone() : new ByteWord(bw));
    this.currentStep = 0;
    this.historyValues = [this.byteWords.map(bw => bw.value)];
  }

  clone() {
    const clonedSystem = new QuineSystem([]); // Use constructor for initial setup, then overwrite
    clonedSystem.byteWords = this.byteWords.map(bw => bw.clone());
    clonedSystem.currentStep = this.currentStep;
    // Deep copy history values
    clonedSystem.historyValues = this.historyValues.map(stepValues => [...stepValues]);
    return clonedSystem;
  }
}

// --- React Components ---

// Display Component
const ByteWordDisplay = ({ byteWord, index }) => {
  const isOuterCActive = byteWord.outer_c === 1;
  const bgColor = isOuterCActive ? '#e6fffa' : '#fff0f0'; // Greenish for active, Reddish for settled
  const borderColor = isOuterCActive ? '#38a169' : '#c53030';

  const containerStyle = {
    border: `2px solid ${borderColor}`,
    borderRadius: '5px', padding: '10px', margin: '5px', minWidth: '160px',
    backgroundColor: bgColor, display: 'flex', flexDirection: 'column',
    alignItems: 'center', textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    fontSize: '12px', fontFamily: 'monospace',
  };
  const headerStyle = { fontWeight: 'bold', marginBottom: '5px', fontSize: '14px' };
  const bitStyle = { letterSpacing: '1px', marginBottom: '5px', fontSize: '16px' };
  const detailStyle = { marginTop: '3px', color: '#555' };
  const modeStyle = { fontWeight: 'bold', color: borderColor, marginTop: '5px' };
  const anchorStyle = { color: '#c53030', fontWeight: 'bold' };
  const pointableStyle = { color: '#38a169', fontWeight: 'bold' };

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>Word {index + 1} ({byteWord.value})</div>
      <div style={bitStyle}>
        {`<${byteWord.outerC_bin}`} <span title={`Dunder C (Bit 6): ${byteWord.dunderC_bin}`}>{byteWord.dunderC_bin}</span> {`${byteWord.coreVV_bin} | ${byteWord.t_bin}>`}
      </div>
      <div style={detailStyle}>Hex: {byteWord.toHex()}</div>
      <div style={modeStyle}>Mode: {byteWord.op_mode}</div>
      <div style={detailStyle}>Op ({byteWord.effective_morphism}): {byteWord.getMorphismDescription()}</div>
      {!isOuterCActive && ( // Only show anchor/pointable status if Outer C = 0
        <div style={detailStyle}>
          Internal State (_C_={byteWord.internal_c}): {byteWord.is_pointable ?
            <span style={pointableStyle}>Pointable</span> :
            <span style={anchorStyle}>Anchored</span>
          }
        </div>
      )}
    </div>
  );
};

// Editor Component (Simplified: Input raw value)
const InitialStateEditor = ({ initialWords, setInitialWords }) => {
    const handleAdd = () => {
        const randomVal = Math.floor(Math.random() * 256);
        setInitialWords(prev => [...prev, new ByteWord(randomVal)]);
    };

    const handleRemove = (index) => {
        if (initialWords.length <= 1) return;
        setInitialWords(prev => prev.filter((_, i) => i !== index));
    };

    const handleChange = (index, event) => {
        const rawValue = parseInt(event.target.value, 10);
        if (!isNaN(rawValue) && rawValue >= 0 && rawValue <= 255) {
            setInitialWords(prev => {
                const next = [...prev];
                next[index] = new ByteWord(rawValue);
                return next;
            });
        } else if (event.target.value === '') {
             setInitialWords(prev => {
                const next = [...prev];
                next[index] = new ByteWord(0); // Default to 0 if empty
                return next;
            });
        }
    };

    return (
        <div className="mb-6 p-4 border rounded-lg shadow-md bg-blue-50">
            <h2 className="text-xl font-semibold mb-4 text-gray-700">Initial Configuration</h2>
            <div className="flex flex-wrap gap-4 items-start">
                {initialWords.map((bw, index) => (
                    <div key={index} className="flex flex-col items-center p-2 border rounded bg-white">
                        <ByteWordDisplay byteWord={bw} index={index} />
                        <input
                            type="number"
                            min="0"
                            max="255"
                            value={bw.value}
                            onChange={(e) => handleChange(index, e)}
                            className="mt-2 p-1 border rounded w-20 text-center text-sm"
                            aria-label={`Value for Word ${index + 1}`}
                        />
                        <button
                            onClick={() => handleRemove(index)}
                            disabled={initialWords.length <= 1}
                            className="mt-1 px-2 py-0.5 bg-red-500 text-white text-xs rounded hover:bg-red-600 disabled:bg-gray-400"
                            aria-label={`Remove Word ${index + 1}`}
                        >
                            Remove
                        </button>
                    </div>
                ))}
                <div className="flex items-center self-center ml-4">
                    <button
                        onClick={handleAdd}
                        className="px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600 shadow"
                        aria-label="Add a new random ByteWord"
                    >
                        + Add Random
                    </button>
                </div>
            </div>
        </div>
    );
};


// Main Simulator Component
const QuineSystemSimulator = () => {
  const [initialByteWords, setInitialByteWords] = useState([
    new ByteWord(0b11001010), // C=1, _C_=1, VV=00, T=1010 (Op Mode VVV, Op=4)
    new ByteWord(0b00101100), // C=0, _C_=0, VV=10, T=1100 (Op Mode VV, Op=2, Anchored)
    new ByteWord(0b01110001), // C=0, _C_=1, VV=11, T=0001 (Op Mode VV, Op=3, Pointable)
  ]);

  const [quineSystem, setQuineSystem] = useState(() => new QuineSystem(initialByteWords));
  const [isRunning, setIsRunning] = useState(false);
  const [isStable, setIsStable] = useState(false);
  const [runUntilStableMode, setRunUntilStableMode] = useState(false);
  const [maxStableSteps] = useState(1000); // Safety break for run until stable
  const historyRef = useRef(new Set()); // For stability check
  const runIntervalRef = useRef(null);

  // Reset simulation when initial state changes
  useEffect(() => {
    setQuineSystem(new QuineSystem(initialByteWords));
    setIsStable(false);
    historyRef.current.clear();
    historyRef.current.add(new QuineSystem(initialByteWords).getStateHash()); // Add initial hash
    if (isRunning) setIsRunning(false); // Stop if running
  }, [initialByteWords]);

  // Simulation Step Logic
  const performStep = useCallback(() => {
    setQuineSystem(prevSystem => {
      const nextSystem = prevSystem.clone();
      const changed = nextSystem.step(); // step() now returns if change occurred
      const currentHash = nextSystem.getStateHash();

      if (!changed || historyRef.current.has(currentHash)) {
        setIsStable(true);
        setIsRunning(false); // Stop running
        setRunUntilStableMode(false); // Turn off mode
        console.log(`System stabilized or repeated state at step ${nextSystem.currentStep}.`);
      } else {
        historyRef.current.add(currentHash);
        setIsStable(false); // Mark as not stable if change occurred
      }

      // Safety break for runUntilStable
      if (runUntilStableMode && nextSystem.currentStep > maxStableSteps) {
          console.warn(`Run Until Stable exceeded max steps (${maxStableSteps}). Stopping.`);
          setIsStable(false); // Not necessarily stable, just stopped
          setIsRunning(false);
          setRunUntilStableMode(false);
      }

      return nextSystem;
    });
  }, [runUntilStableMode, maxStableSteps]); // Dependencies for the step logic

  // Manual Step Handler
  const handleStep = () => {
    if (!isRunning && !isStable) {
      performStep();
    }
  };

  // Run/Pause Handler
  const handleToggleRun = () => {
    if (isRunning) {
      setIsRunning(false);
      setRunUntilStableMode(false); // Ensure stable mode stops on manual pause
    } else if (!isStable) {
      setIsRunning(true);
      setRunUntilStableMode(false); // Normal run mode
      historyRef.current.clear(); // Clear history for normal run stability check
      historyRef.current.add(quineSystem.getStateHash());
    }
  };

  // Run Until Stable Handler
  const handleRunUntilStable = () => {
      if (!isRunning && !isStable) {
          setIsRunning(true);
          setRunUntilStableMode(true); // Activate stable mode
          historyRef.current.clear(); // Clear history for stability check
          historyRef.current.add(quineSystem.getStateHash());
      }
  };

  // Reset Handler
  const handleReset = () => {
    setIsRunning(false);
    setRunUntilStableMode(false);
    setIsStable(false);
    setQuineSystem(new QuineSystem(initialByteWords));
    historyRef.current.clear();
    historyRef.current.add(new QuineSystem(initialByteWords).getStateHash());
  };

  // Effect for continuous running
  useEffect(() => {
    if (isRunning && !isStable) {
      // Use interval for normal run, direct calls for runUntilStable
      if (!runUntilStableMode) {
          runIntervalRef.current = setInterval(performStep, 200); // Adjust speed as needed
      } else {
          // Rapidly step when in runUntilStable mode
          const runLoop = () => {
              if (runUntilStableMode && isRunning && !isStable) { // Check flags again inside loop
                  performStep();
                  // Use requestAnimationFrame for tight loop without blocking UI entirely
                  requestAnimationFrame(runLoop);
              }
          };
          requestAnimationFrame(runLoop);
      }
    } else {
      if (runIntervalRef.current) {
        clearInterval(runIntervalRef.current);
        runIntervalRef.current = null;
      }
    }
    // Cleanup interval on unmount or when isRunning/isStable changes
    return () => {
      if (runIntervalRef.current) {
        clearInterval(runIntervalRef.current);
      }
    };
  }, [isRunning, isStable, runUntilStableMode, performStep]); // Include performStep


  return (
    <div className="container mx-auto p-4 md:p-6 lg:p-8 font-sans">
      <h1 className="text-3xl font-bold mb-6 text-center text-gray-800">Thermo-Quine ByteWord Playground</h1>

      <InitialStateEditor initialWords={initialByteWords} setInitialWords={setInitialByteWords} />

      {/* Simulation Controls Section */}
      <section className="mb-8 p-4 border rounded-lg shadow-md bg-gray-50">
         <h2 className="text-xl font-semibold mb-4 text-gray-700">Simulation Controls</h2>
         <div className="flex flex-wrap items-center gap-4">
           <button onClick={handleStep} disabled={isRunning || isStable} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed shadow"> Step </button>
           <button onClick={handleToggleRun} disabled={isStable} className={`px-4 py-2 ${isRunning && !runUntilStableMode ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'} text-white rounded transition-colors shadow disabled:bg-gray-400 disabled:cursor-not-allowed`} aria-live="polite"> {isRunning && !runUntilStableMode ? 'Pause' : 'Run'} </button>
           <button onClick={handleRunUntilStable} disabled={isRunning || isStable} className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed shadow"> Run Until Stable </button>
           <button onClick={handleReset} className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors shadow"> Reset </button>
           {isStable && <span className="ml-4 font-bold text-green-700">System Stable!</span>}
           {isRunning && runUntilStableMode && <span className="ml-4 font-bold text-purple-700">Running until stable...</span>}
         </div>
      </section>

      {/* Current State Display Section */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Current State (Step {quineSystem.currentStep})</h2>
        <div className="flex flex-wrap gap-3 p-4 border rounded-lg bg-gray-100 min-h-[100px] max-h-[450px] overflow-y-auto shadow-inner">
          {quineSystem.byteWords.length > 0 ? (
             quineSystem.byteWords.map((byteWord, index) => (
                <ByteWordDisplay
                    key={`current-${index}-${byteWord.value}-${quineSystem.currentStep}`} // Key includes step for re-render
                    byteWord={byteWord}
                    index={index}
                />
             ))
            ) : ( <div className="text-gray-500 w-full text-center py-4">System is empty.</div> )}
        </div>
      </section>

      {/* Basic History (Optional) */}
      {<section>
          <h3 className="text-lg font-semibold mb-2">Value History (Last 10)</h3>
          <pre className="text-xs bg-gray-200 p-2 rounded overflow-x-auto">
              {quineSystem.historyValues.slice(-10).map((vals, idx) => `Step ${quineSystem.currentStep - quineSystem.historyValues.slice(-10).length + 1 + idx}: [${vals.join(', ')}]`).join('\n')}
          </pre>
      </section>}

    </div>
  );
};

export default QuineSystemSimulator;