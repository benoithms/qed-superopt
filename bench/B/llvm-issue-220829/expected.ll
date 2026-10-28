define noundef zeroext i1 @f(i8 noundef zeroext %0) {
  %2 = and i8 %0, 127
  %3 = icmp ne i8 %2, 0
  call void @llvm.assume(i1 %3)
  %4 = icmp ult i8 %0, 8
  ret i1 %4
}
declare void @llvm.assume(i1 noundef)
