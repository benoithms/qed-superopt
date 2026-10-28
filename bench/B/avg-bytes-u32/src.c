#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b) {
    uint32_t r = 0;
    r |= (((a & 0xff) + (b & 0xff)) >> 1);
    r |= ((((a >> 8) & 0xff) + ((b >> 8) & 0xff)) >> 1) << 8;
    r |= ((((a >> 16) & 0xff) + ((b >> 16) & 0xff)) >> 1) << 16;
    r |= (((a >> 24) + (b >> 24)) >> 1) << 24;
    return r;
}
