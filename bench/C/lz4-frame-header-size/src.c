#include <stdint.h>
uint64_t f(uint32_t m, uint8_t g) {
    if ((m & 0xfffffff0u) == 0x184d2a50u)
        return 8;
    if (m != 0x184d2204u)
        return (uint64_t)-13;
    return 7 + (((g >> 3) & 1) ? 8 : 0) + ((g & 1) ? 4 : 0);
}
