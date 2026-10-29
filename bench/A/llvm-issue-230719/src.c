#include <stdint.h>
uint32_t f(uint32_t x) { return ((x & 12) * 17) & 48; }
