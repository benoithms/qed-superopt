#include <stdint.h>
int32_t f(int32_t a) {
    if (a < 0 || a > 1)
        __builtin_unreachable();
    return 1 << a;
}
