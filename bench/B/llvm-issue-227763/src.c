#include <stdint.h>
int32_t f(uint8_t x) { return ((int32_t)(uint8_t)(x ^ 3) - 1) >> 31; }
