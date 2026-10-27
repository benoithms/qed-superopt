#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t x, bool c) {
    uint32_t y = c ? 0u - x : x;
    return y == 0;
}
