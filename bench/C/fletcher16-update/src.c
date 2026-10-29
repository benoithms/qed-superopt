#include <stdint.h>
uint16_t f(uint16_t s, uint8_t d) {
    uint32_t a = s & 0xff;
    uint32_t b = s >> 8;
    a = (a + d) % 255;
    b = (b + a) % 255;
    return (uint16_t)((b << 8) | a);
}
