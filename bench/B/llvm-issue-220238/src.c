#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t b, uint32_t o) {
    uint64_t a = (uint64_t)b + o;
    return a + 4 <= (uint64_t)b + 62;
}
