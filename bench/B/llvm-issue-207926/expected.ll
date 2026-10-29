define zeroext i1 @f(i64 noundef %0) {
  %2 = icmp ne i64 %0, 0
  ret i1 %2
}
