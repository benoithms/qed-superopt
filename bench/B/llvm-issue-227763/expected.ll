define range(i32 -1, 1) i32 @f(i8 noundef zeroext %0) {
  %2 = icmp eq i8 %0, 3
  %3 = sext i1 %2 to i32
  ret i32 %3
}
