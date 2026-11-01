#include <stdint.h>
int32_t f(int64_t a) {
    if (a >= 0)
        return (int32_t)((a + 0xffffffffll) >> 32);
    else
        return (int32_t)((a - 0xffffffffll) >> 32);
}
