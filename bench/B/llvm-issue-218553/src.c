#include <stdint.h>
uint32_t f(uint32_t x, uint32_t y) {
    if ((x & y) != 0)
        __builtin_unreachable();
    return x ^ y;
}
