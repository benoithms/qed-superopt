#include <stdbool.h>
#include <stdint.h>
bool f(uint64_t y) { return __builtin_popcountll(y) | y; }
