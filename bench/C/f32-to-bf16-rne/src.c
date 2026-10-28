#include <stdint.h>
uint16_t f(uint32_t x) {
    if ((x & 0x7fffffffu) > 0x7f800000u)
        return (uint16_t)((x >> 16) | 0x40);
    return (uint16_t)((x + 0x7fffu + ((x >> 16) & 1)) >> 16);
}
