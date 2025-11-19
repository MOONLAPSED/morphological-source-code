// Demonstrate floating-point non-associativity
console.log("Floating-point non-associativity example:");
const a = 0.1;
const b = 0.2;
const c = 0.3;

const result1 = (a + b) + c;
const result2 = a + (b + c);

console.log(`(a + b) + c = ${result1}`);
console.log(`a + (b + c) = ${result2}`);
console.log(`Equal? ${result1 === result2}`);
console.log(`Difference: ${result1 - result2}`);

// Binary representation to see the issue
function getBinaryFloatRepresentation(num) {
  const buffer = new ArrayBuffer(8);
  const float64 = new Float64Array(buffer);
  float64[0] = num;
  const uint8 = new Uint8Array(buffer);
  
  // Extract binary parts
  let binary = '';
  for (let i = 7; i >= 0; i--) {
    let byte = uint8[i].toString(2);
    // Pad with leading zeros
    binary += '0'.repeat(8 - byte.length) + byte;
  }
  
  // First bit is sign
  const sign = binary[0];
  // Next 11 bits are exponent
  const exponent = binary.substring(1, 12);
  // Remaining 52 bits are mantissa
  const mantissa = binary.substring(12);
  
  return {
    value: num,
    binary: binary,
    sign: sign,
    exponent: exponent,
    mantissa: mantissa
  };
}

console.log("\nBinary representation of 0.1:");
console.log(getBinaryFloatRepresentation(0.1));