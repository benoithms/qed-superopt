define i32 @f(i32 noundef %0, i32 noundef %1) {
  %3 = ashr i32 %0, %1
  ret i32 %3
}
