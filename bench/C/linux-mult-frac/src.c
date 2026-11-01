#include <stdint.h>
uint32_t f(uint32_t x, uint32_t n, uint32_t d) {
    uint32_t q = x / d;
    uint32_t r = x % d;
    return q * n + r * n / d;
}
