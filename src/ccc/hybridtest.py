import cffi
ffi = cffi.FFI()

ffi.cdef("""
typedef struct {
    uint8_t bits[64];
    size_t size;
} PreNumberSet;

typedef struct {
    PreNumberSet local;
    PreNumberSet *shared;
} KernelState;

void kernel_cycle(KernelState *k, uint8_t rotation);
const uint8_t* kernel_get_entangled(const KernelState *k);
""")

C = ffi.dlopen("./kernel.so")  # compiled shared object

# Initialize
local = ffi.new("PreNumberSet *")
local.size = 8
for i in range(8):
    local.bits[i] = i*3

shared = ffi.new("PreNumberSet *")
shared.size = 8
for i in range(8):
    shared.bits[i] = i*7

kstate = ffi.new("KernelState *")
kstate.local = local[0]
kstate.shared = shared

# Python observes the entangled pre-numbers
entangled = ffi.cast("uint8_t *", C.kernel_get_entangled(kstate))
print(list(entangled[:shared.size]))

# Perform a deterministic cycle
C.kernel_cycle(kstate, 42)
print(list(entangled[:shared.size]))