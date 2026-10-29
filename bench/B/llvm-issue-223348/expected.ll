define noundef zeroext i1 @f(i32 noundef %0) {
  %2 = icmp sgt i32 %0, 0
  ret i1 %2
}
