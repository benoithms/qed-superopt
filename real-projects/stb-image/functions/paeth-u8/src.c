#include <stdint.h>
int32_t f(uint8_t a, uint8_t b, uint8_t c) {
    int32_t thresh = c * 3 - (a + b);
    int32_t lo = a < b ? a : b;
    int32_t hi = a < b ? b : a;
    int32_t t0 = (hi <= thresh) ? lo : c;
    int32_t t1 = (thresh <= lo) ? hi : t0;
    return t1;
}
