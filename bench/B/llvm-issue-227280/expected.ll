define range(i32 0, 19) i32 @f(i32 noundef %0) {
  %2 = and i32 %0, 2
  %3 = mul nuw nsw i32 %2, 9
  ret i32 %3
}
