#include <stdint.h>
int32_t f(uint32_t c) {
    if (c < 0xffu)
        return ((c + 1) & 0x7f) >= 0x21;
    if (c < 0x2028u || c - 0x202au < 0xd800 - 0x202a || c - 0xe000u < 0xfff9 - 0xe000)
        return 1;
    if (c - 0xfffcu > 0x10ffff - 0xfffc || (c & 0xfffe) == 0xfffe)
        return 0;
    return 1;
}
