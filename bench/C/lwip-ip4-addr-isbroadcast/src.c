#include <stdint.h>
uint8_t f(uint32_t a, uint8_t fl, uint32_t ip, uint32_t m) {
    if (~a == 0 || a == 0)
        return 1;
    else if ((fl & 0x02) == 0)
        return 0;
    else if (a == ip)
        return 0;
    else if ((a & m) == (ip & m) && (a & ~m) == (0xffffffffu & ~m))
        return 1;
    else
        return 0;
}
