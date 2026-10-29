#include <stdint.h>
int32_t f(int32_t a, int32_t s) {
    return s == 1 ? (a >> 1) + (a & 1) : ((a >> (s - 1)) + 1) >> 1;
}
