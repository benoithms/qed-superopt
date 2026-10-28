#include <stdint.h>
uint32_t f(uint32_t a, uint64_t d) {
    return (d < 31) ? a >> d | ((uint32_t)(a << (-d & 31)) != 0) : (a != 0);
}
