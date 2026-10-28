#include <stdint.h>
uint8_t f(int32_t x, int32_t y) {
    int32_t s = x + y;
    if (s < 0) return 0;
    if (s > 255) return 255;
    return (uint8_t)s;
}
