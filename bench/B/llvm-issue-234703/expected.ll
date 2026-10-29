define noundef zeroext i1 @f(i32 noundef %0, i32 noundef %1, i32 noundef %2) {
  %4 = icmp ne i32 %2, 0
  %5 = and i32 %0, 8
  %6 = icmp eq i32 %5, 0
  %7 = and i1 %4, %6
  %8 = icmp sgt i32 %1, 1
  %9 = and i1 %7, %8
  ret i1 %9
}
