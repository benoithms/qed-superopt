#include <stdint.h>
int32_t f(int32_t x) {
    int32_t z = x ? __builtin_clz((uint32_t)x) : 32;
    int32_t r = 24 - z;
    uint32_t u = (uint32_t)x;
    uint32_t v;
    if (r == 0)
        v = u;
    else if (r < 0)
        v = (u << (uint32_t)-r) | (u >> (32 - (uint32_t)-r));
    else
        v = (u << (32 - (uint32_t)r)) | (u >> (uint32_t)r);
    int32_t q = v & 0x7f;
    int32_t y = (int32_t)(q + (((int64_t)(q * (128 - q)) * 179) >> 16));
    return y + (int32_t)((uint32_t)(31 - z) << 7);
}
