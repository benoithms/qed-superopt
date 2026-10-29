#include <stdint.h>
uint32_t f(uint32_t lo, uint32_t hi) {
    __builtin_assume(lo <= hi && hi <= 31);
    uint32_t upper = hi == 31 ? 0xffffffffu : (1u << (hi + 1)) - 1;
    uint32_t lower = (1u << lo) - 1;
    return upper & ~lower;
}
