define i32 @f(i32 noundef %0, i32 noundef %1) {
  %3 = icmp ule i32 %0, %1
  call void @llvm.assume(i1 %3)
  %4 = icmp ult i32 %1, 32
  call void @llvm.assume(i1 %4)
  %5 = sub nuw nsw i32 31, %1
  %6 = lshr i32 -1, %5
  %7 = shl nsw i32 -1, %0
  %8 = and i32 %6, %7
  ret i32 %8
}
declare void @llvm.assume(i1 noundef)
