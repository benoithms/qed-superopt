#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t addr, uint32_t size) { return (addr & 3) + size > 4 && size > 1; }
