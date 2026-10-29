define zeroext i1 @f(i64 noundef %0, i64 noundef %1) {
  %3 = icmp ult i64 %0, %1
  ret i1 %3
}
