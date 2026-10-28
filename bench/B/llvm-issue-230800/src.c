#include <stdbool.h>
#include <stdint.h>
bool f(int8_t x) { return (uint8_t)(x + 1) < 3 && (uint8_t)(x & 0x81) == 0x81; }
