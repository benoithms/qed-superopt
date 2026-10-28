#include <stdint.h>
uint64_t f(uint64_t a, uint64_t b, uint64_t c) {
    uint64_t p, q;
    if (__builtin_mul_overflow(a, b, &p))
        p = UINT64_MAX;
    if (__builtin_mul_overflow(p, c, &q))
        q = UINT64_MAX;
    return q;
}
