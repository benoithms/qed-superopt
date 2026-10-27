#include <stdbool.h>
#include <stdint.h>
bool f(uint16_t x) { return __builtin_clz(__builtin_bitreverse16(x)) == __builtin_ctzg(x) + 16; }
