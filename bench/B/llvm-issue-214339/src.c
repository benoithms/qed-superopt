#include <stdint.h>
uint8_t f(uint32_t x) { return (uint8_t)(((x << 12) + 34816u) >> 8); }
