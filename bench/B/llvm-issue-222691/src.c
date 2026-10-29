#include <stdbool.h>
#include <stdint.h>
bool f(int32_t x) {
    uint64_t p;
    bool o = __builtin_mul_overflow((uint64_t)(int64_t)x, (uint64_t)3, &p);
    return !o && p < 41;
}
