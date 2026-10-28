#include <stdint.h>
uint16_t f(uint64_t n) {
    if (n < 10) {
        return (uint16_t)(n - 2);
    } else if (n < 134) {
        uint32_t b = (31u ^ (uint32_t)__builtin_clz((uint32_t)(n - 6))) - 1u;
        return (uint16_t)((b << 1) + ((n - 6) >> b) + 4);
    } else if (n < 2118) {
        return (uint16_t)((31u ^ (uint32_t)__builtin_clz((uint32_t)(n - 70))) + 12);
    } else {
        return 23u;
    }
}
