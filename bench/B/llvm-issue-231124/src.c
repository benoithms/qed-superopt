#include <stdint.h>
uint32_t f(uint64_t x) {
    uint32_t lo = (uint32_t)x;
    uint32_t hi = (uint32_t)(x >> 32);
    if (lo != 0)
        return (uint32_t)__builtin_ctz(lo);
    if (hi != 0)
        return 32 + (uint32_t)__builtin_ctz(hi);
    return 32;
}
