define noundef zeroext i1 @f(i8 noundef zeroext %0) {
  %2 = and i8 %0, -3
  %3 = icmp ne i8 %2, 8
  ret i1 %3
}
