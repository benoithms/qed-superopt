#include <stdint.h>
uint32_t f(uint32_t a, uint64_t n, uint32_t s, uint32_t k) {
    uint32_t hi = (31 - (uint32_t)__builtin_clz((uint32_t)(n - 1))) - k;
    uint32_t t = a;
    uint32_t lo1 = (31 - (uint32_t)__builtin_clz((uint32_t)n)) + 1;
    uint32_t lo2 = (31 - (uint32_t)__builtin_clz(s)) + 2;
    uint32_t lo = lo1 < lo2 ? lo1 : lo2;
    if (t == 0) t = 11;
    if (hi < t) t = hi;
    if (lo > t) t = lo;
    if (t < 5) t = 5;
    if (t > 12) t = 12;
    return t;
}
