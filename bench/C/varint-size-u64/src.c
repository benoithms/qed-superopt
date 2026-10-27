#include <stdint.h>
uint32_t f(uint64_t x) {
    if (x < (1ull << 7)) return 1;
    if (x < (1ull << 14)) return 2;
    if (x < (1ull << 21)) return 3;
    if (x < (1ull << 28)) return 4;
    if (x < (1ull << 35)) return 5;
    if (x < (1ull << 42)) return 6;
    if (x < (1ull << 49)) return 7;
    if (x < (1ull << 56)) return 8;
    if (x < (1ull << 63)) return 9;
    return 10;
}
