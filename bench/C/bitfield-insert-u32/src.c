#include <stdint.h>

uint32_t f(uint32_t x, int32_t pos, int32_t len, uint32_t v) {
    __builtin_assume(pos >= 0 && len > 0 && len <= 32 - pos);
    uint32_t mask = (~0u >> (32 - len)) << pos;
    return (x & ~mask) | ((v << pos) & mask);
}
