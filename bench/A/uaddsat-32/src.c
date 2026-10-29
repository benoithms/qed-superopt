#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b) {
    uint32_t s = a + b;
    return s < a ? UINT32_MAX : s;
}
