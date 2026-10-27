#include <stdint.h>
uint32_t f(uint32_t x, uint32_t i, uint32_t j) {
    uint32_t a = (x >> i) & 1;
    uint32_t b = (x >> j) & 1;
    x &= ~((1u << i) | (1u << j));
    return x | (a << j) | (b << i);
}
