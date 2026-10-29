#include <stdint.h>
int64_t f(uint32_t a, uint32_t b) {
    int64_t d = (int64_t)a - (int64_t)b;
    return a > b ? d : -d;
}
