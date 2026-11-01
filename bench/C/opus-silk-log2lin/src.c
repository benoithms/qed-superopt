#include <stdint.h>
int32_t f(int32_t x) {
    if (x < 0)
        return 0;
    else if (x >= 3967)
        return INT32_MAX;
    int32_t y = (int32_t)((uint32_t)1 << (x >> 7));
    int32_t q = x & 0x7f;
    int32_t p = (int32_t)(int16_t)q * (int32_t)(int16_t)(128 - q);
    int32_t k = (int32_t)(q + (((int64_t)p * -174) >> 16));
    if (x < 2048)
        y = y + ((y * k) >> 7);
    else
        y = y + (y >> 7) * k;
    return y;
}
