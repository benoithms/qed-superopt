#include <stdint.h>
uint8_t f(uint8_t a, uint8_t b, uint8_t c, uint8_t x) {
    int32_t p = b - c;
    int32_t q = a - c;
    int32_t u = p < 0 ? -p : p;
    int32_t v = q < 0 ? -q : q;
    int32_t w = (p + q) < 0 ? -(p + q) : p + q;
    int32_t r = a;
    if (v < u) {
        u = v;
        r = b;
    }
    if (w < u)
        r = c;
    return (uint8_t)(r + x);
}
