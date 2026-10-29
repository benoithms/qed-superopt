#include <stdint.h>
uint64_t f(uint64_t n, uint64_t a, uint64_t b) {
    if ((n & 15) == 0)
        return a;
    if (n == 16)
        return b;
    return 0;
}
