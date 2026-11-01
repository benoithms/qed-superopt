#include <stdint.h>
uint16_t f(uint16_t a, uint16_t b, int32_t c) {
    uint16_t lo = (uint16_t)((b & 0x7u) | ((a & 0x7u) << 3u));
    if (c && a < 8u && b < 16u) {
        return (b < 8u) ? lo : (lo | 64u);
    } else {
        uint32_t k = 2u * ((b >> 3u) + 3u * (a >> 3u));
        k = (k << 5u) + 0x40u + ((0x520D40u >> k) & 0xC0u);
        return (uint16_t)(k | lo);
    }
}
