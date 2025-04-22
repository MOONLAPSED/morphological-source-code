// Let's analyze the ByteWord implementation
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
      this._state = "SUPERPOSITION"; // Changed from enum reference
    }
  
    // Test a few ByteWord instances
    static test() {
      // Test case 1: ByteWord initialization
      console.log("Test ByteWord initialization:");
      const test1 = new ByteWord(0x29); // 0010|1001
      console.log(`Raw: ${test1.raw}, Value: ${test1.value}`);
      console.log(`State data: ${test1.state_data}, Morphism: ${test1.morphism}, Floor morphic: ${test1.floor_morphic}`);
      console.log(`toString: ${test1.toString()}, toHex: ${test1.toHex()}`);
      
      // Test case 2: Different ByteWord
      const test2 = new ByteWord(0x35); // 0011|0101
      console.log("\nTest ByteWord 2:");
      console.log(`Raw: ${test2.raw}, Value: ${test2.value}`);
      console.log(`State data: ${test2.state_data}, Morphism: ${test2.morphism}, Floor morphic: ${test2.floor_morphic}`);
      
      // Test case 3: Transform operations
      console.log("\nTest transformations:");
      // Test identity transform (morphism 0)
      const identity = new ByteWord(0x00); // morphism 0
      const transformed1 = identity.transform(test1);
      console.log(`Identity transform: ${test1.toString()} => ${transformed1.toString()}`);
      
      // Test copy transform (morphism 1)
      const copy = new ByteWord(0x02); // morphism 1
      const transformed2 = copy.transform(test1);
      console.log(`Copy transform: original ${test1.toString()}, transformed ${transformed2.toString()}`);
      
      // Test XNOR transform (morphism 3)
      const xnor = new ByteWord(0x07); // morphism 3, floor_morphic 1
      const transformed3 = xnor.transform(test1);
      console.log(`XNOR transform: original ${test1.toString()}, transformed ${transformed3.toString()}`);
      
      return { test1, test2, transformed1, transformed2, transformed3 };
    }
    
    toString() {
      return `${this.state_data.toString(2).padStart(4, '0')}|${this.morphism.toString(2).padStart(3, '0')}${this.floor_morphic}`;
    }
  
    toHex() {
      return `0x${this.value.toString(16).padStart(2, '0')}`;
    }
  
    get _pointable() {
      return this.floor_morphic === 1; // Changed from Morphology.DYNAMIC
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
  
  // Test the ByteWord class
  const testResults = ByteWord.test();
  
  // Now let's test the QuineSystem implementation
  class QuineSystem {
    constructor(initialByteWords) {
      this.byteWords = [...initialByteWords];
      this.replicationHistory = [this.byteWords.map(bw => bw.value)];
      this.currentStep = 0;
    }
  
    step() {
      if (this.byteWords.length === 0) return;
      
      // Create a copy of the current state
      const newByteWords = [...this.byteWords];
      
      // Process each ByteWord based on its morphism
      for (let i = 0; i < this.byteWords.length; i++) {
        const current = this.byteWords[i];
        const targetIndex = (i + 1) % this.byteWords.length; // Point to next ByteWord
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
  }
  
  // Test the QuineSystem with the sample ByteWords
  console.log("\n\nQuineSystem Test:");
  const initialByteWords = [
    new ByteWord(0x29), // 0010|1001 - Copy Transform
    new ByteWord(0x35), // 0011|0101 - Swap Nibbles Transform
    new ByteWord(0x11)  // 0001|0001 - Copy Transform
  ];
  
  console.log("Initial ByteWords:");
  initialByteWords.forEach((bw, i) => {
    console.log(`${i}: ${bw.toString()} (${bw.toHex()}) - State: ${bw.state_data}, Morphism: ${bw.morphism}, Control: ${bw.floor_morphic}`);
  });
  
  const quineSystem = new QuineSystem(initialByteWords);
  
  // Run 3 steps and analyze results
  console.log("\nSimulation Steps:");
  for (let i = 0; i < 3; i++) {
    const result = quineSystem.step();
    console.log(`\nStep ${i+1} - ByteWord count: ${result.length}`);
    result.forEach((bw, j) => {
      console.log(`${j}: ${bw.toString()} (${bw.toHex()}) - State: ${bw.state_data}, Morphism: ${bw.morphism}, Control: ${bw.floor_morphic}`);
    });
  }
  
  // Check bug: Is the system actually replicating as expected?
  console.log("\nReplication History Length Check:");
  console.log(`Initial count: ${initialByteWords.length}`);
  quineSystem.replicationHistory.forEach((state, step) => {
    console.log(`Step ${step}: ${state.length} ByteWords`);
  });
  
  // Check if specific transformations work as expected
  console.log("\nSpecific transform tests:");
  
  // Test XNOR transform logic
  const xnorSource = new ByteWord(0x37); // morphism 3, control 1
  const xnorTarget = new ByteWord(0x5A);
  const xnorResult = xnorSource.transform(xnorTarget);
  console.log(`XNOR transform: ${xnorSource.toString()} applied to ${xnorTarget.toString()} = ${xnorResult.toString()}`);
  
  // Test swap nibbles
  const swapSource = new ByteWord(0x0A); // morphism 5, control 0
  const swapTarget = new ByteWord(0x5A);
  const swapResult = swapSource.transform(swapTarget);
  console.log(`Swap nibbles: ${swapSource.toString()} applied to ${swapTarget.toString()} = ${swapResult.toString()}`);