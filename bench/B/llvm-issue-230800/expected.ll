define noundef zeroext i1 @f(i8 noundef signext %0) {
  %2 = icmp eq i8 %0, -1
  ret i1 %2
}
