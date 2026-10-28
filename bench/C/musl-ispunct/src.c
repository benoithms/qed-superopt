#include <stdint.h>
int32_t f(int32_t c) {
    return (uint32_t)c - 0x21 < 0x5e && !((((uint32_t)c | 32) - 'a' < 26) || ((uint32_t)c - '0' < 10));
}
