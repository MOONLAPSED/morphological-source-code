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

// 4. Test QuineSystem behavior with problematic patterns
console.log("\nTesting QuineSystem with potential problematic patterns:");

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
    this._state = 'SUPERPOSITION';
  }

  get _pointable() {
    return this.floor_morphic === 1;
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

// Test case 1: All copy transforms - should grow exponentially
console.log("Test case 1: All copy transforms");

const allCopy = [
  new ByteWord(0x11), // T=1, V=0, C=1 (Copy)
  new ByteWord(0x21), // T=2, V=0, C=1 (Copy)
  new ByteWord(0x31)  // T=3, V=0, C=1 (Copy)
].map(bw => {
  // Set all to copy transform (V=1)
  return new ByteWord((bw.state_data << 4) | (1 << 1) | bw.floor_morphic);
});

const system1 = new QuineSystem(allCopy);
console.log("Initial:", system1.byteWords.map(bw => bw.toString()));

for (let i = 0; i < 3; i++) {
  system1.step();
  console.log(`Step ${i+1} (${system1.byteWords.length} ByteWords):`, 
              system1.byteWords.slice(0, 5).map(bw => bw.toString()) + 
              (system1.byteWords.length > 5 ? "..." : ""));
}

// Test case 2: Empty initial state
console.log("\nTest case 2: Empty initial state");
try {
  const emptySystem = new QuineSystem([]);
  console.log("Initial:", emptySystem.byteWords);
  
  // Should handle empty state gracefully
  emptySystem.step();
  console.log("After step:", emptySystem.byteWords);
} catch (e) {
  console.log("Error with empty system:", e.message);
}

// Test case 3: Random transform behavior
console.log("\nTest case 3: Random transform behavior");
const randomTransform = new ByteWord((3 << 4) | (7 << 1) | 1); // T=3, V=7 (Random), C=1
console.log("Random transform ByteWord:", randomTransform.toString());

const target = new ByteWord(0x51); // T=5, V=0, C=1
console.log("Target before:", target.toString());

// Apply transform multiple times and check result is different
const results = [];
for (let i = 0; i < 5; i++) {
  const result = randomTransform.transform(target);
  results.push(result.toString());
  console.log(`Transform ${i+1} result:`, result.toString());
}

// Check if we have at least some different results (it's random, so should be different)
const uniqueResults = new Set(results);
console.log("Number of unique results:", uniqueResults.size);
console.log("Results should be somewhat random");