#include <stdint.h>
int64_t f(int32_t x) {
    __builtin_assume((uint32_t)x + 1u < 3u);
    return (x > 0) - (x < 0);
}
