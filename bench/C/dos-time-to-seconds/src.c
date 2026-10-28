#include <stdint.h>
uint32_t f(uint16_t t) {
    uint32_t h = t >> 11;
    uint32_t m = (t >> 5) & 0x3f;
    uint32_t s = t & 0x1f;
    return h * 3600 + m * 60 + s * 2;
}
