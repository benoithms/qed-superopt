#include <stdint.h>
int32_t f(int32_t a, int32_t b) {
    int32_t r = a % b;
    if (r != 0 && ((r < 0) != (b < 0)))
        r += b;
    return r;
}
