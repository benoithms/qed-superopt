#include <stdint.h>
uint32_t f(uint8_t x) {
    return (x & 1) + ((x >> 1) & 1) + ((x >> 2) & 1) + ((x >> 3) & 1) +
           ((x >> 4) & 1) + ((x >> 5) & 1) + ((x >> 6) & 1) + (x >> 7);
}
