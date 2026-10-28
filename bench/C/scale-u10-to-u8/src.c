#include <stdint.h>
uint8_t f(uint16_t x) {
    uint32_t v = x > 1023 ? 1023 : x;
    return (uint8_t)((v * 255 + 511) / 1023);
}
