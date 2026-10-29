define i32 @f(i32 noundef %0, i32 noundef %1, i32 noundef %2) {
  %4 = lshr i32 %0, %1
  %5 = lshr i32 %0, %2
  %6 = xor i32 %4, %5
  %7 = and i32 %6, 1
  %8 = shl i32 %7, %1
  %9 = shl i32 %7, %2
  %10 = or i32 %8, %9
  %11 = xor i32 %0, %10
  ret i32 %11
}
