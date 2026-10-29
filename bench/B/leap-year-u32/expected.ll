define noundef zeroext i1 @f(i32 noundef %0) {
  %2 = urem i32 %0, 25
  %3 = icmp eq i32 %2, 0
  %4 = select i1 %3, i32 15, i32 3
  %5 = and i32 %0, %4
  %6 = icmp eq i32 %5, 0
  ret i1 %6
}
