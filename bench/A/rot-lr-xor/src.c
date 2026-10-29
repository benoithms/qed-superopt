#include <stdint.h>
uint32_t f(uint32_t x, uint32_t n, uint32_t m) {
    uint32_t l = (x << (n & 31)) | (x >> ((32 - n) & 31));
    uint32_t r = (x >> (m & 31)) | (x << ((32 - m) & 31));
    return l ^ r;
}
