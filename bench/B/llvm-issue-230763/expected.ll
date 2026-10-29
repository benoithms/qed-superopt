define noundef zeroext i1 @f(i64 noundef %0) {
  %2 = trunc i64 %0 to i32
  %3 = icmp ne i64 %0, 0
  %4 = icmp slt i32 %2, 1
  %5 = xor i1 %3, %4
  ret i1 %5
}
