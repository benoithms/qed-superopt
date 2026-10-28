#include <stdint.h>
int32_t f(int32_t x) {
    int32_t p;
    if (__builtin_mul_overflow(x, 3, &p))
        __builtin_unreachable();
    return p / 2;
}
