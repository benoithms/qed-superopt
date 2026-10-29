#include <stdint.h>
uint64_t f(uint64_t s, uint64_t v) {
    return s ? (((s << 3) - s) + (v << 10)) >> 3 : (v << 10);
}
