define noundef range(i64 -1, 2) i64 @f(i32 noundef %0) {
  %2 = add i32 %0, 1
  %3 = icmp ult i32 %2, 3
  call void @llvm.assume(i1 %3)
  %4 = sext i32 %0 to i64
  ret i64 %4
}
declare void @llvm.assume(i1 noundef)
