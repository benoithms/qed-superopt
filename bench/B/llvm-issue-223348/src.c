#include <stdbool.h>
#include <stdint.h>
bool f(int32_t x) { return x > (int32_t)(0u - (uint32_t)x); }
