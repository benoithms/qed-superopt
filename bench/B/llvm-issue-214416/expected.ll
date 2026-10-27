define range(i64 1, 17) i64 @f(i64 noundef %0) {
  %2 = or i64 %0, 1
  %3 = call i64 @llvm.ctlz.i64(i64 %2, i1 true)
  %4 = sub nuw nsw i64 67, %3
  %5 = lshr i64 %4, 2
  ret i64 %5
}
declare i64 @llvm.ctlz.i64(i64, i1)
