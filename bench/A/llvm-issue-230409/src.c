#include <stdbool.h>
#include <stdint.h>
bool f(int64_t x) { return x < 1 && x % 1000000 > 0; }
