define range(i32 0, 2) i32 @f(i8 noundef zeroext %0) {
  %2 = call i8 @llvm.ctpop.i8(i8 %0)
  %3 = and i8 %2, 1
  %4 = zext nneg i8 %3 to i32
  ret i32 %4
}
declare i8 @llvm.ctpop.i8(i8)
