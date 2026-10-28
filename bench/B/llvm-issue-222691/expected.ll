define noundef zeroext i1 @f(i32 noundef %0) {
  %2 = icmp ult i32 %0, 14
  ret i1 %2
}
