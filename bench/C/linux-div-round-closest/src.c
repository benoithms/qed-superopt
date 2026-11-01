#include <stdint.h>
int32_t f(int32_t x, int32_t d) {
    return ((x > 0) == (d > 0)) ? (x + d / 2) / d : (x - d / 2) / d;
}
