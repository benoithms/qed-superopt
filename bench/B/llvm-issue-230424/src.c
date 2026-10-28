#include <stdbool.h>
#include <stdint.h>
bool f(int64_t x, int64_t y) { return ((x + y) | y) == 0; }
