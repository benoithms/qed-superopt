#include <stdint.h>
int32_t f(int64_t a, int64_t b) {
    if (a < b) return -1;
    if (a > b) return 1;
    return 0;
}
