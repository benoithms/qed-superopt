define noundef range(i32 0, 16) i32 @f(i32 noundef %0) {
  %2 = and i32 %0, 15
  ret i32 %2
}
