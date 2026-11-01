#include <stdint.h>
int32_t f(uint8_t a, uint8_t b, uint8_t c) {
    int32_t n = a;
    if (n > 0x7f) {
        if (n == 0xff)
            n = (b | (c << 8)) + 0x7f00;
        else
            n = ((n - 0x80) << 8) + b;
    }
    return n;
}
