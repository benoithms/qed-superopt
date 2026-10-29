#include <stdint.h>
uint32_t f(uint32_t x) { return ((x & 2) * 9) & 22; }
