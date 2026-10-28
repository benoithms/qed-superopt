define zeroext i1 @f(i32 noundef %0, i32 noundef %1) {
  %3 = icmp ult i32 %1, 59
  ret i1 %3
}
