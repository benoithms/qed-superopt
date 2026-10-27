#include <stdbool.h>
#include <stdint.h>
bool f(uint64_t a, uint64_t b) {
    uint32_t a1 = (uint32_t)(a >> 32), b1 = (uint32_t)(b >> 32);
    uint32_t a0 = (uint32_t)a, b0 = (uint32_t)b;
    return a1 == b1 ? a0 < b0 : a1 < b1;
}
