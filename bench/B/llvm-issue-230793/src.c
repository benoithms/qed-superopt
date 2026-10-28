#include <stdint.h>
int32_t f(int32_t x) {
    int32_t v = (int32_t)((uint32_t)x | 0x80000000u) + 1;
    return (uint32_t)v < 3 ? 0 : v;
}
