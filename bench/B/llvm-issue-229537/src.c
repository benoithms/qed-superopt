#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t x, uint32_t y) { return (x == 1 && y == 0) ? y != x : x > y; }
