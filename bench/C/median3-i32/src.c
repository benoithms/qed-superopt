#include <stdint.h>
int32_t f(int32_t a, int32_t b, int32_t c) {
    if (a > b) {
        if (b > c) return b;
        if (a > c) return c;
        return a;
    }
    if (a > c) return a;
    if (b > c) return c;
    return b;
}
