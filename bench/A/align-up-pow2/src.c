#include <stdint.h>
uint64_t f(uint64_t x, uint32_t k) {
    uint64_t a = (uint64_t)1 << (k & 63);
    return (x + a - 1) & ~(a - 1);
}
