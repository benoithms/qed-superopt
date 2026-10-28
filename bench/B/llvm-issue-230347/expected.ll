define zeroext i1 @f(i64 noundef %0, i64 noundef %1) {
  %3 = sub i64 %0, %1
  %4 = and i64 %3, 1
  %5 = icmp eq i64 %4, 0
  ret i1 %5
}
