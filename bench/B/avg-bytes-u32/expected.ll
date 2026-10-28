define i32 @f(i32 noundef %0, i32 noundef %1) {
  %3 = and i32 %0, %1
  %4 = xor i32 %0, %1
  %5 = and i32 %4, -16843010
  %6 = lshr i32 %5, 1
  %7 = add i32 %3, %6
  ret i32 %7
}
