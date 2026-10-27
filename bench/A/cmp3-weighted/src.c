#include <stdint.h>
int32_t f(int32_t a, int32_t b, uint32_t c, uint32_t d) {
    int32_t r1 = (a > b) - (a < b);
    int32_t r2 = (c > d) - (c < d);
    return r1 * 3 + r2;
}
