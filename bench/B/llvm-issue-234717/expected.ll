define noundef zeroext i1 @f(i32 noundef %0) {
  %2 = icmp ne i32 %0, 4
  %3 = trunc i32 %0 to i1
  %4 = xor i1 %2, %3
  ret i1 %4
}
