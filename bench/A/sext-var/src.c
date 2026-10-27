#include <stdint.h>
int32_t f(int32_t x, uint32_t n) {
    uint32_t s = (32 - (n & 31)) & 31;
    return (int32_t)((uint32_t)x << s) >> s;
}
