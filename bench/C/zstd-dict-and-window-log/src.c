#include <stdint.h>
uint32_t f(uint32_t w, uint64_t s, uint64_t d) {
    if (d == 0)
        return w;
    uint64_t ws = 1ull << w;
    uint64_t t = d + ws;
    if (ws >= d + s)
        return w;
    if (t >= (1ull << 31))
        return 31;
    return (31 - (uint32_t)__builtin_clz((uint32_t)t - 1)) + 1;
}
