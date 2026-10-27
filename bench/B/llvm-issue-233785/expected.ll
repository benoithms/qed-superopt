define noundef zeroext i1 @f(i1 noundef zeroext %0, i64 noundef %1, i64 noundef %2) {
  %4 = icmp sgt i64 %2, %1
  %5 = and i1 %0, %4
  ret i1 %5
}
