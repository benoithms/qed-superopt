#include <stdint.h>
uint64_t f(uint64_t n) {
    return n >= 0xff00ff00ff00ff00ull ? 0 : n + (n >> 8) + (n < (128 << 10) ? ((128 << 10) - n) >> 11 : 0);
}
