#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b, uint32_t c) {
    uint32_t m = a < b ? a : b;
    uint32_t n = a > b ? a : b;
    return (m < c ? c : m) + (n < c ? n : c);
}
