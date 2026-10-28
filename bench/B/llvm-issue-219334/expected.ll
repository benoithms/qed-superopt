define noundef i64 @f(i64 noundef %0) {
  %2 = shl i64 %0, 1
  %3 = xor i64 %2, -1
  %4 = and i64 %0, %3
  ret i64 %4
}
