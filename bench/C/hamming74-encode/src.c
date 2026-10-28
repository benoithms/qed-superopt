#include <stdint.h>
uint8_t f(uint8_t d) {
    uint32_t b0 = d & 1, b1 = (d >> 1) & 1, b2 = (d >> 2) & 1, b3 = (d >> 3) & 1;
    uint32_t c0 = b0 ^ b1 ^ b3;
    uint32_t c1 = b0 ^ b2 ^ b3;
    uint32_t c2 = b1 ^ b2 ^ b3;
    return (uint8_t)(c0 | (c1 << 1) | (b0 << 2) | (c2 << 3) | (b1 << 4) | (b2 << 5) | (b3 << 6));
}
