define i32 @f(i32 noundef %0, i32 noundef %1, i32 noundef %2) {
  %4 = call i32 @llvm.umax.i32(i32 %0, i32 %1)
  %5 = call i32 @llvm.umin.i32(i32 %0, i32 %1)
  %6 = sub i32 %4, %5
  %7 = call i32 @llvm.umax.i32(i32 %1, i32 %2)
  %8 = call i32 @llvm.umin.i32(i32 %1, i32 %2)
  %9 = sub i32 %7, %8
  %10 = add i32 %6, %9
  ret i32 %10
}
declare i32 @llvm.umax.i32(i32, i32)
declare i32 @llvm.umin.i32(i32, i32)
