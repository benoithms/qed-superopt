define i32 @f(i32 noundef %0) {
  %2 = add i32 %0, -1
  %3 = call i32 @llvm.ctlz.i32(i32 %2, i1 false)
  %4 = zext nneg i32 %3 to i64
  %5 = lshr i64 4294967296, %4
  %6 = trunc i64 %5 to i32
  ret i32 %6
}
declare i32 @llvm.ctlz.i32(i32, i1)
