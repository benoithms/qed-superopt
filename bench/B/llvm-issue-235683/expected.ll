define noundef i64 @f(i64 noundef %0) {
  %2 = add i64 %0, -8
  %3 = and i64 %0, -8
  %4 = xor i64 %3, %2
  ret i64 %4
}
