define noundef zeroext i1 @f(i8 noundef zeroext %0, i8 noundef zeroext %1) {
  %3 = add i8 %1, 12
  %4 = icmp eq i8 %0, %3
  call void @llvm.assume(i1 %4)
  ret i1 false
}
declare void @llvm.assume(i1 noundef)
