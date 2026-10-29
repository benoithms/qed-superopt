define noundef zeroext i1 @f(i32 noundef %0) {
  %2 = add i32 %0, -16843009
  %3 = xor i32 %0, -1
  %4 = and i32 %2, %3
  %5 = and i32 %4, -2139062144
  %6 = icmp ne i32 %5, 0
  ret i1 %6
}
