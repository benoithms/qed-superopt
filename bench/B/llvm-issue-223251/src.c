#include <stdbool.h>
#include <stdint.h>
bool f(uint8_t x) {
    uint8_t v = x - 8;
    return v > 2 || v == 1;
}
