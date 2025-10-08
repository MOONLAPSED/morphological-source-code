#include <stdint.h>
#include <stddef.h>

#define MAX_ENTANGLED 64

typedef struct {
    uint8_t bits[MAX_ENTANGLED];  // entangled “pre-math numbers”
    size_t size;
} PreNumberSet;

typedef struct {
    PreNumberSet local;           // observable local delta
    PreNumberSet *shared;         // pointer to shared entangled set
} KernelState;

// deterministic nudge of a pre-number
static inline void nudge_pre_number(uint8_t *x, uint8_t rotation) {
    *x = (*x + rotation) & 0xFF;  // simple deterministic quasi-random nudge
}

// evolve a kernel state
void kernel_cycle(KernelState *k, uint8_t rotation) {
    for (size_t i=0;i<k->local.size;i++) {
        nudge_pre_number(&k->local.bits[i], rotation);
    }
    if (k->shared) {
        for (size_t i=0;i<k->shared->size;i++) {
            nudge_pre_number(&k->shared->bits[i], rotation);
        }
    }
}

// read-only access for Python
const uint8_t* kernel_get_entangled(const KernelState *k) {
    return k->shared ? k->shared->bits : NULL;
}
