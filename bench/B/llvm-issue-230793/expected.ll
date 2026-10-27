define range(i32 -2147483647, 1) i32 @f(i32 noundef %0) {
  %2 = or i32 %0, -2147483648
  %3 = add nsw i32 %2, 1
  ret i32 %3
}
