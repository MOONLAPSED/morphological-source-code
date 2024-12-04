constexpr u64 a = 0b0001'0001; // Binary representation: 0001 (lane 1) | 0001 (lane 2)
constexpr u64 b = 0b0010'0010; // Binary representation: 0010 (lane 1) | 0010 (lane 2)
constexpr u64 c = 0b0011'0011; // Expected sum of `a` and `b` (lane-wise): 0011 (3) | 0011 (3)

static_assert(a + b == c);     // Compile-time check that lane-wise addition is correct

constexpr u64 a = 0b0001'0001'0001'0001; // Lanes: 1 | 1 | 1 | 1
constexpr u64 b = 0b0010'0010'0010'0010; // Lanes: 2 | 2 | 2 | 2
constexpr u64 c = 0b0011'0011'0011'0011; // Result: 3 | 3 | 3 | 3

static_assert(a + b == c); // Still valid across all lanes

// Overflow and Masking
constexpr u64 a = 0b0000'0001'0001'0001; // Lanes: 0 | 1 | 1 | 1
constexpr u64 b = 0b0000'1111'0010'0010; // Lanes: 0 | 15 | 2 | 2
constexpr u64 c = 0b0001'0000'0011'0011; // Incorrect: Lane overflow corrupts result

static_assert(a + b == c); // FAILS
