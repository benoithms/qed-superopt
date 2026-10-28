#include <stdint.h>
int32_t f(int32_t a) {
    if (a != 10 && a != 11)
        __builtin_unreachable();
    return (a != 10) == (a - 10);
}
