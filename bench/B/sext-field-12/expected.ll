define range(i32 -4096, 4096) i32 @f(i32 noundef %0) {
  %2 = shl i32 %0, 16
  %3 = ashr i32 %2, 20
  ret i32 %3
}
