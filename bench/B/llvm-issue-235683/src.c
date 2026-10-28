#include <stdint.h>
uint64_t f(uint64_t x) {
    uint64_t a = x - 8;
    return (((a & ~(uint64_t)7) + 8)) ^ a;
}
