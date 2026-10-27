#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b) { return (a & b) + ((a ^ b) >> 1); }
