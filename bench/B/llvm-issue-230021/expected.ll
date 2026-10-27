define i32 @f(i32 noundef %0) {
  %2 = mul i32 %0, 1536
  %3 = and i32 %2, -2048
  ret i32 %3
}
