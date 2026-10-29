#include <stdint.h>
uint32_t f(uint32_t a, uint32_t b) {
    return 0x10000 + (((a & 0x3ff) << 10) | (b & 0x3ff));
}
