define range(i32 0, 2) i32 @f(i32 noundef %0) {
  %2 = and i32 %0, -2
  %3 = icmp eq i32 %2, 10
  call void @llvm.assume(i1 %3)
  ret i32 1
}
declare void @llvm.assume(i1 noundef)
