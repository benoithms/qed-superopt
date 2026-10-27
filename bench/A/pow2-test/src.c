#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t x) { return x != 0 && (x & (x - 1)) == 0; }
