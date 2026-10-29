#include <stdint.h>
uint32_t f(uint32_t x, uint32_t n) { return ((x ^ -(x >> 31)) >> n) ^ -(x >> 31); }
