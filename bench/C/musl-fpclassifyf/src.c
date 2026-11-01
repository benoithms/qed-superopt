#include <stdint.h>
int32_t f(uint32_t x) {
    int32_t e = x >> 23 & 0xff;
    if (!e)
        return x << 1 ? 3 : 2;
    if (e == 0xff)
        return x << 9 ? 0 : 1;
    return 4;
}
