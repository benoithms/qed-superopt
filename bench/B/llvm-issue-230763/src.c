#include <stdbool.h>
#include <stdint.h>
bool f(int64_t x) {
    int32_t t = (int32_t)x;
    int64_t s = t == 0 ? 0 : (t < 1 ? -1 : 1);
    return s == (int64_t)(x != 0);
}
