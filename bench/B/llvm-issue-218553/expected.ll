define noundef i32 @f(i32 noundef %0, i32 noundef %1) {
  %3 = and i32 %1, %0
  %4 = icmp eq i32 %3, 0
  call void @llvm.assume(i1 %4)
  %5 = or disjoint i32 %1, %0
  ret i32 %5
}
declare void @llvm.assume(i1 noundef)
