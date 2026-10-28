#include <stdint.h>
int64_t f(int64_t a, int64_t b, int64_t c) {
    int64_t lo = a < b ? a : b;
    lo = lo < c ? lo : c;
    int64_t hi = a > b ? a : b;
    hi = hi > c ? hi : c;
    return hi - lo;
}
