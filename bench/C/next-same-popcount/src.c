#include <stdint.h>
uint32_t f(uint32_t x) {
    uint32_t s = x & (0u - x);
    uint32_t r = x + s;
    uint32_t o = ((x ^ r) >> 2) / s;
    return r | o;
}
