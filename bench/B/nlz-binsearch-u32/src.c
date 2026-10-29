#include <stdint.h>
uint32_t f(uint32_t x) {
    if (x == 0)
        return 32;
    uint32_t n = 0;
    if ((x & 0xffff0000u) == 0) { n += 16; x <<= 16; }
    if ((x & 0xff000000u) == 0) { n += 8; x <<= 8; }
    if ((x & 0xf0000000u) == 0) { n += 4; x <<= 4; }
    if ((x & 0xc0000000u) == 0) { n += 2; x <<= 2; }
    if ((x & 0x80000000u) == 0) { n += 1; }
    return n;
}
