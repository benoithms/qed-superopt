define noundef zeroext i1 @f(i64 noundef %0) {
  %2 = add i64 %0, -250
  %3 = icmp ult i64 %2, -499
  ret i1 %3
}
