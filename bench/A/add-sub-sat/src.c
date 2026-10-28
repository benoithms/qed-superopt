#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b, uint32_t c) {
    uint32_t s = a + b;
    s = s < a ? UINT32_MAX : s;
    return s > c ? s - c : 0;
}
