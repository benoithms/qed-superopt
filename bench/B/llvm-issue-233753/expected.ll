define noundef zeroext i1 @f(i32 noundef %0, i1 noundef zeroext %1) {
  %3 = icmp eq i32 %0, 0
  ret i1 %3
}
