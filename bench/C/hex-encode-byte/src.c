#include <stdint.h>
uint16_t f(uint8_t x) {
    uint32_t hi = x >> 4;
    uint32_t lo = x & 0xf;
    uint32_t c0 = hi < 10 ? '0' + hi : 'a' + hi - 10;
    uint32_t c1 = lo < 10 ? '0' + lo : 'a' + lo - 10;
    return (uint16_t)(c0 | (c1 << 8));
}
