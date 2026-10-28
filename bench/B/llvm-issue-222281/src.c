#include <stdint.h>
uint32_t f(uint8_t x) {
    uint8_t v = (x & 0xf8) | 0x80;
    return 64u >> (__builtin_ctz(v) - 3);
}
