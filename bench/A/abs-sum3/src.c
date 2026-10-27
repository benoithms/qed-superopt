#include <stdint.h>
int32_t f(int32_t a, int32_t b, int32_t c) {
    int32_t x = a < 0 ? -a : a;
    int32_t y = b < 0 ? -b : b;
    int32_t z = c < 0 ? -c : c;
    return x + y + z;
}
