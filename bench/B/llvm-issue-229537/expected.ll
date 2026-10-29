define noundef zeroext i1 @f(i32 noundef %0, i32 noundef %1) {
  %3 = icmp ugt i32 %0, %1
  ret i1 %3
}
