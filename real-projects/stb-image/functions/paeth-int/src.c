int f(int a, int b, int c) {
    int thresh = c * 3 - (a + b);
    int lo = a < b ? a : b;
    int hi = a < b ? b : a;
    int t0 = (hi <= thresh) ? lo : c;
    int t1 = (thresh <= lo) ? hi : t0;
    return t1;
}
