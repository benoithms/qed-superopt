#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t y) { return (y % 4 == 0 && y % 100 != 0) || y % 400 == 0; }
