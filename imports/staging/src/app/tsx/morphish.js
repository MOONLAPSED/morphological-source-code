import React, { useState } from 'react';
import './App.css';

/** === ByteWord Core === **/
class ByteWord {
  constructor(raw) {
    if (raw < 0 || raw > 0xFF) throw new Error('ByteWord must be 0–255');
    this.raw = raw;
  }

  get T() { return (this.raw >> 4) & 0x0F; }
  get V() { return (this.raw >> 1) & 0x07; }
  get C() { return this.raw & 0x01; }

  toBinary() { return this.raw.toString(2).padStart(8, '0'); }
  toHex()    { return '0x' + this.raw.toString(16).padStart(2, '0'); }
  toDecimal(){ return this.raw.toString(10); }
  toOctal()  { return '0o' + this.raw.toString(8); }

  static identity(bw) {
    return new ByteWord(bw.raw);
  }

  static operators = {
    0: { name: 'Identity', fn: ByteWord.identity },
    // Future operators can be added here
  };
}

/** === Tile Card View === **/
function ByteWordCard({ bw, showBin, showDec, showHex, showOct }) {
  return (
    <div className="tile">
      <h3>Quine Tile</h3>
      {showBin && <p><strong>Binary:</strong> {bw.toBinary()}</p>}
      {showDec && <p><strong>Decimal:</strong> {bw.toDecimal()}</p>}
      {showHex && <p><strong>Hex:</strong> {bw.toHex()}</p>}
      {showOct && <p><strong>Octal:</strong> {bw.toOctal()}</p>}
      <p><strong>T:</strong> {bw.T} | <strong>V:</strong> {bw.V} | <strong>C:</strong> {bw.C}</p>
    </div>
  );
}

/** === Main Playground Component === **/
export default function App() {
  const [input, setInput] = useState('00101001');
  const [op, setOp] = useState('0');
  const [results, setResults] = useState([]);

  const [showBin, setShowBin] = useState(true);
  const [showDec, setShowDec] = useState(true);
  const [showHex, setShowHex] = useState(true);
  const [showOct, setShowOct] = useState(false);

  const handleRun = () => {
    try {
      const raw = input.startsWith('0x')
        ? parseInt(input, 16)
        : parseInt(input.replace(/[^01]/g, ''), 2);
      if (isNaN(raw) || raw < 0 || raw > 0xFF) throw Error();

      const bw = new ByteWord(raw);
      const { fn } = ByteWord.operators[op];
      const result = fn(bw);
      setResults([...results, result]); // support multiple tiles
    } catch {
      alert('Invalid ByteWord. Use 8-bit binary or 0xNN hex.');
    }
  };

  return (
    <div className="app">
      <h1>Morphism Playground</h1>

      <div className="controls">
        <label>
          ByteWord:
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="0x29 or 00101001"
          />
        </label>

        <label>
          Operator:
          <select value={op} onChange={e => setOp(e.target.value)}>
            {Object.entries(ByteWord.operators).map(([k, { name }]) => (
              <option key={k} value={k}>{k} – {name}</option>
            ))}
          </select>
        </label>

        <button onClick={handleRun}>Run</button>

        <fieldset className="toggle-group">
          <legend>Display Formats</legend>
          <label><input type="checkbox" checked={showBin} onChange={() => setShowBin(!showBin)} /> Bin</label>
          <label><input type="checkbox" checked={showDec} onChange={() => setShowDec(!showDec)} /> Dec</label>
          <label><input type="checkbox" checked={showHex} onChange={() => setShowHex(!showHex)} /> Hex</label>
          <label><input type="checkbox" checked={showOct} onChange={() => setShowOct(!showOct)} /> Oct</label>
        </fieldset>
      </div>

      <div className="tile-grid">
        {results.map((bw, idx) => (
          <ByteWordCard
            key={idx}
            bw={bw}
            showBin={showBin}
            showDec={showDec}
            showHex={showHex}
            showOct={showOct}
          />
        ))}
      </div>

      <style jsx>{`
        .app {
          font-family: monospace;
          max-width: 800px;
          margin: auto;
          padding: 1rem;
        }
        .controls {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          margin-bottom: 1rem;
        }
        .controls input, select {
          margin-left: 0.5rem;
        }
        .toggle-group {
          display: flex;
          gap: 1rem;
          margin-top: 0.5rem;
        }
        .tile-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1rem;
        }
        .tile {
          border: 1px solid #ccc;
          padding: 1rem;
          border-radius: 8px;
          background: #f3f3f3;
        }
        .tile h3 {
          margin-top: 0;
        }
      `}</style>
    </div>
  );
}
