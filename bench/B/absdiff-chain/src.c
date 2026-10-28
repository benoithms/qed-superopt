#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b, uint32_t c) {
    uint32_t d1 = a > b ? a - b : b - a;
    uint32_t d2 = b > c ? b - c : c - b;
    return d1 + d2;
}
