#include <stdint.h>
int32_t f(uint32_t x) {
    int32_t v = (int32_t)((x >> 4) & 0xfff);
    if (v & 0x800)
        v -= 0x1000;
    return v;
}
