#include <stdint.h>
uint64_t f(int64_t n, int64_t s) {
    uint64_t a = ((uint64_t)n + (n >> 3) + 6) & ~(uint64_t)3;
    if (n - s > (int64_t)(a - n))
        a = ((uint64_t)n + 3) & ~(uint64_t)3;
    if (n == 0)
        a = 0;
    return a;
}
