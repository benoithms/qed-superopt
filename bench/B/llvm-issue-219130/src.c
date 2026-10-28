#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b, uint32_t c) {
    if (a < 39 || a > 46)
        __builtin_unreachable();
    if (b < 1 || b > 2)
        __builtin_unreachable();
    if (c < 184 || c > 194)
        __builtin_unreachable();
    return c / a - b;
}
