define noundef zeroext i1 @f(i32 noundef %0, i32 noundef %1) {
  %3 = and i32 %0, 3
  %4 = add i32 %3, %1
  %5 = icmp ugt i32 %4, 4
  ret i1 %5
}
