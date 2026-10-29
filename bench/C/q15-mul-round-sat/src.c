#include <stdint.h>
int16_t f(int16_t a, int16_t b) {
    int32_t p = ((int32_t)a * b + (1 << 14)) >> 15;
    if (p > 32767) p = 32767;
    if (p < -32768) p = -32768;
    return (int16_t)p;
}
