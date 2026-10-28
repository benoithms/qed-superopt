#include <stdbool.h>
#include <stdint.h>
bool f(uint8_t a, uint8_t b) {
    __builtin_assume(a == (uint8_t)(b + 12));
    return a == b;
}
