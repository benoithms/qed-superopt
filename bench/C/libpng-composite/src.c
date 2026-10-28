#include <stdint.h>
uint8_t f(uint8_t fg, uint8_t a, uint8_t bg) {
    uint16_t t = (uint16_t)((uint16_t)fg * (uint16_t)a + (uint16_t)bg * (uint16_t)(255 - (uint16_t)a) + 128);
    return (uint8_t)(((t + (t >> 8)) >> 8) & 0xff);
}
