define zeroext i1 @f(i64 noundef %0, i64 noundef %1) {
  %3 = or i64 %0, %1
  %4 = icmp eq i64 %3, 0
  ret i1 %4
}
