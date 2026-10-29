#include <stdbool.h>
#include <stdint.h>
bool f(bool c, int64_t a, int64_t b) {
    if (c && a == b)
        return false;
    int64_t v = c ? b : a;
    return v > a;
}
