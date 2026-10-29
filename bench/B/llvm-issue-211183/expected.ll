define i16 @f(i16 noundef zeroext %0, i16 noundef zeroext %1) {
  %3 = icmp ult i16 %0, 2
  %4 = select i1 %3, i16 %0, i16 0
  %5 = shl i16 %1, %4
  ret i16 %5
}
