#include <stdint.h>
uint32_t f(uint32_t s, uint8_t d) {
    s ^= d & 0xf;
    s = (s & 1) ? (s >> 1) ^ 0xedb88320u : s >> 1;
    s = (s & 1) ? (s >> 1) ^ 0xedb88320u : s >> 1;
    s = (s & 1) ? (s >> 1) ^ 0xedb88320u : s >> 1;
    s = (s & 1) ? (s >> 1) ^ 0xedb88320u : s >> 1;
    return s;
}
