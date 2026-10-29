#include <stdint.h>
int16_t f(uint8_t u) {
    uint32_t v = (uint8_t)~u;
    int32_t m = (int32_t)(((v & 0x0f) << 3) + 0x84) << ((v >> 4) & 7);
    m -= 0x84;
    return (int16_t)((v & 0x80) ? -m : m);
}
