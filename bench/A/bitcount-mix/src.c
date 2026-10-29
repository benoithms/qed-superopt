#include <stdint.h>
uint32_t f(uint32_t x) {
    return (uint32_t)__builtin_popcount(x) + (uint32_t)__builtin_ctz(x | 0x80000000u) + (uint32_t)__builtin_clz(x | 1u);
}
