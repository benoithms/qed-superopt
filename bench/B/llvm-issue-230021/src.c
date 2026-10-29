#include <stdint.h>
uint32_t f(uint32_t x) { return (x >> 4) * 24576u + (((x & 15) * 1536u) & 30720u); }
