#include <stdint.h>
uint64_t f(uint64_t h, uint64_t d, uint32_t m) {
    switch (m) {
    case 0:
    case 2:
    case 3:
        break;
    case 1:
        d = 0;
        break;
    default:
        break;
    }
    int u = h == (0ull - 1);
    uint64_t e = u && d > 0 ? 500 : 0;
    return u && d == 0 ? (0ull - 1) : h + d + e;
}
