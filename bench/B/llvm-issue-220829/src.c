#include <stdbool.h>
#include <stdint.h>
bool f(uint8_t x) {
    __builtin_assume((uint8_t)(x + x) != 0);
    return (uint8_t)(x - 1) < 7;
}
