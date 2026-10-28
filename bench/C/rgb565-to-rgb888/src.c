#include <stdint.h>
uint32_t f(uint16_t c) {
    uint32_t r = (c >> 11) & 0x1f;
    uint32_t g = (c >> 5) & 0x3f;
    uint32_t b = c & 0x1f;
    r = (r << 3) | (r >> 2);
    g = (g << 2) | (g >> 4);
    b = (b << 3) | (b >> 2);
    return (r << 16) | (g << 8) | b;
}
