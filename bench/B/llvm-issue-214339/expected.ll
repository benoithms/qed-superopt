define i8 @f(i32 noundef %0) {
  %2 = shl i32 %0, 4
  %3 = add i32 %2, 136
  %4 = trunc i32 %3 to i8
  ret i8 %4
}
