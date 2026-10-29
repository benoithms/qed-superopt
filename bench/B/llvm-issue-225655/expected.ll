define noundef i64 @f(i64 noundef %0, i64 noundef %1, i64 noundef %2) {
  %4 = and i64 %0, 15
  %5 = icmp eq i64 %4, 0
  %6 = select i1 %5, i64 %1, i64 0
  ret i64 %6
}
