#include <stdbool.h>
#include <stdint.h>
bool f(uint32_t x) {
    return (x & 0xffu) == 0 || (x & 0xff00u) == 0 || (x & 0xff0000u) == 0 || (x & 0xff000000u) == 0;
}
