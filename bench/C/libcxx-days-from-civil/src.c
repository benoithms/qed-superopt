#include <stdint.h>
int32_t f(int16_t y, uint8_t m, uint8_t d) {
    int32_t t = y - (m <= 2);
    uint32_t mm = m;
    uint32_t dd = d;
    int32_t q = (t >= 0 ? t : t - 399) / 400;
    uint32_t r = (uint32_t)(t - q * 400);
    uint32_t s = (153 * (mm + (mm > 2 ? -3 : 9)) + 2) / 5 + dd - 1;
    uint32_t u = r * 365 + r / 4 - r / 100 + s;
    return q * 146097 + (int32_t)u - 719468;
}
