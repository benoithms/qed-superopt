define range(i32 0, 33) i32 @f(i32 noundef %0) {
  %2 = call i32 @llvm.ctlz.i32(i32 %0, i1 false)
  ret i32 %2
}
declare i32 @llvm.ctlz.i32(i32, i1)
