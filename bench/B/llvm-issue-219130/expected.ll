define range(i32 2, 4) i32 @f(i32 noundef %0, i32 noundef %1, i32 noundef %2) {
  %4 = add i32 %0, -39
  %5 = icmp ult i32 %4, 8
  call void @llvm.assume(i1 %5)
  %6 = add i32 %1, -1
  %7 = icmp ult i32 %6, 2
  call void @llvm.assume(i1 %7)
  %8 = add i32 %2, -184
  %9 = icmp ult i32 %8, 11
  call void @llvm.assume(i1 %9)
  %10 = sub nuw nsw i32 4, %1
  ret i32 %10
}
declare void @llvm.assume(i1 noundef)
