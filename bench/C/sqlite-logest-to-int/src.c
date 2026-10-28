#include <stdint.h>
uint64_t f(int16_t x) {
    uint64_t n = x % 10;
    x /= 10;
    if (n >= 5)
        n -= 2;
    else if (n >= 1)
        n -= 1;
    if (x > 60)
        return 0x7fffffffffffffffull;
    return x >= 3 ? (n + 8) << (x - 3) : (n + 8) >> (3 - x);
}
