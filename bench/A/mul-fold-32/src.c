#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b) {
    uint64_t p = (uint64_t)a * b;
    return (uint32_t)p ^ (uint32_t)(p >> 32);
}
