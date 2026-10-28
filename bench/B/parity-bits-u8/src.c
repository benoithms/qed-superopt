#include <stdint.h>
uint32_t f(uint8_t x) {
    return (x ^ (x >> 1) ^ (x >> 2) ^ (x >> 3) ^ (x >> 4) ^ (x >> 5) ^ (x >> 6) ^ (x >> 7)) & 1;
}
