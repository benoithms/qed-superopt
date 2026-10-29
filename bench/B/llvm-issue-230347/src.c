#include <stdbool.h>
#include <stdint.h>
bool f(uint64_t a, uint64_t b) {
    uint64_t t = a - (((a - b) & ~(uint64_t)1) + b);
    return t == (t & ~(uint64_t)3);
}
