define noundef zeroext i1 @f(i8 noundef zeroext %0, i32 noundef %1) {
  %3 = and i8 %0, -2
  %4 = icmp eq i8 %3, 42
  ret i1 %4
}
