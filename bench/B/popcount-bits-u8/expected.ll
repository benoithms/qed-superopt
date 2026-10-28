define range(i32 0, 9) i32 @f(i8 noundef zeroext %0) {
  %2 = zext i8 %0 to i32
  %3 = call i32 @llvm.ctpop.i32(i32 %2)
  ret i32 %3
}
declare i32 @llvm.ctpop.i32(i32)
