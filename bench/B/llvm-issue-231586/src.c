#include <stdbool.h>
#include <stdint.h>
bool f(uint8_t k, uint32_t p) { return (p == 0 || k != 13) & ((k & 0xfe) == 42); }
