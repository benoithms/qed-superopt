#include <stdint.h>
uint64_t f(uint32_t h) {
    __builtin_assume(h < (1u << 24));
    uint32_t n = h >> 3;
    uint32_t t = (h >> 1) & 3;
    if (t == 1)
        return 1;
    if (t == 3)
        return (uint64_t)-20;
    return n;
}
