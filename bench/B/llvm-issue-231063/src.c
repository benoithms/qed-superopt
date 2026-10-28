#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t x, uint32_t y, uint32_t z) { return (x == 0) & (x + y == z); }
