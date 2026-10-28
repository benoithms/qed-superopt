#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b) { return (uint32_t)(((uint64_t)a * b) >> 32); }
