define noundef zeroext i1 @f(i32 noundef %0, i32 noundef %1, i32 noundef %2) {
  %4 = icmp eq i32 %0, 0
  %5 = icmp eq i32 %1, %2
  %6 = and i1 %4, %5
  ret i1 %6
}
