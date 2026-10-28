#include <stdbool.h>
#include <stdint.h>
bool f(int32_t a, int32_t b) {
    int32_t m = a < b ? a : b;
    return a >= 0 && a <= 15 && b >= 0 && b <= 15 && m > 15;
}
