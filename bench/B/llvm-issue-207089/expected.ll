define range(i32 0, 2) i32 @f(i32 noundef %0) {
  %2 = icmp ult i32 %0, 2
  call void @llvm.assume(i1 %2)
  ret i32 1
}
declare void @llvm.assume(i1 noundef)
