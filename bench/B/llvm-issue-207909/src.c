#include <stdint.h>
int32_t f(int32_t a, int32_t b) { return (a & b) != b ? (a | b) : a; }
