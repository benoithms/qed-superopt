#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t x) { return x != 4 && (x & 1) == 0; }
