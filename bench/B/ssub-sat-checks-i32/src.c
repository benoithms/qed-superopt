#include <stdint.h>
int32_t f(int32_t a, int32_t b) {
    if (b < 0 && a > INT32_MAX + b)
        return INT32_MAX;
    if (b > 0 && a < INT32_MIN + b)
        return INT32_MIN;
    return a - b;
}
