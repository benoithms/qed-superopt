#include <stdint.h>
uint64_t f(uint64_t x) { return x == 0 ? 1 : (uint64_t)(67 - __builtin_clzll(x)) / 4; }
