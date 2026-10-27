#include <stdint.h>
uint64_t f(uint64_t x, uint64_t c) { return (x & c) + ((x & c) ^ c); }
