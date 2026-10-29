#include <stdint.h>
uint16_t f(uint16_t x, uint16_t y) {
    uint16_t b = x < 2 ? x : 0;
    return (uint16_t)((b + 1) * y);
}
