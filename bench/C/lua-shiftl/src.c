#include <stdint.h>
int64_t f(int64_t x, int64_t y) {
    if (y < 0) {
        if (y <= -64)
            return 0;
        return (int64_t)((uint64_t)x >> -y);
    }
    if (y >= 64)
        return 0;
    return (int64_t)((uint64_t)x << y);
}
