#include <stdint.h>
uint32_t f(uint32_t x, uint32_t v, uint32_t pos, uint32_t len) {
    __builtin_assume(len >= 1 && len <= 31 && pos <= 32 - len);
    uint32_t mask = ((1u << len) - 1) << pos;
    return (x & ~mask) | ((v << pos) & mask);
}
