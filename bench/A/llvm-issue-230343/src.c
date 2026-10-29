#include <stdbool.h>
#include <stdint.h>
uint8_t f(uint8_t x, bool y) { return (x & 1) ? y : 0; }
