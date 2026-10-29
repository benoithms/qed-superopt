#include <stdint.h>
uint64_t f(uint64_t x) {
    uint64_t r = __builtin_bitreverse64(x);
    return __builtin_bitreverse64(r & ~(r >> 1));
}
