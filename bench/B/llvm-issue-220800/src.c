#include <stdbool.h>
#include <stdint.h>
bool f(uint64_t x) { return (uint64_t)__builtin_popcountll(x) <= x; }
