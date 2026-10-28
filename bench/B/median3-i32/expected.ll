define noundef i32 @f(i32 noundef %0, i32 noundef %1, i32 noundef %2) {
  %4 = call i32 @llvm.smin.i32(i32 %0, i32 %1)
  %5 = call i32 @llvm.smax.i32(i32 %0, i32 %1)
  %6 = call i32 @llvm.smin.i32(i32 %5, i32 %2)
  %7 = call i32 @llvm.smax.i32(i32 %4, i32 %6)
  ret i32 %7
}
declare i32 @llvm.smin.i32(i32, i32)
declare i32 @llvm.smax.i32(i32, i32)
