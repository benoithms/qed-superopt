#include <stdbool.h>
#include <stdint.h>
bool f(int32_t a, int32_t b) {
    return (b > 0 && a > INT32_MAX - b) || (b < 0 && a < INT32_MIN - b);
}
