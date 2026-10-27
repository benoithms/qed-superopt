#include <stdbool.h>
#include <stdint.h>
bool f(int32_t a, int32_t b, int32_t c) { return (c != 0 || b < 1) && (a & 8) == 0 && b > 1; }
