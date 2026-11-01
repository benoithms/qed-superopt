#include <stdint.h>
uint32_t f(uint32_t a, uint32_t m, uint8_t s1, uint8_t s2) {
    uint32_t t = (uint32_t)(((uint64_t)a * m) >> 32);
    return (t + ((a - t) >> s1)) >> s2;
}
