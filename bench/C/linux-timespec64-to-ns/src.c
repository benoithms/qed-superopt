#include <stdint.h>
int64_t f(int64_t s, int64_t ns) {
    if (s >= 9223372036)
        return INT64_MAX;
    if (s <= -9223372036)
        return INT64_MIN;
    return s * 1000000000 + ns;
}
