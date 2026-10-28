define i8 @f(i32 noundef %0, i32 noundef %1) {
  %3 = add nsw i32 %1, %0
  %4 = call i32 @llvm.smax.i32(i32 %3, i32 0)
  %5 = call i32 @llvm.umin.i32(i32 %4, i32 255)
  %6 = trunc nuw i32 %5 to i8
  ret i8 %6
}
declare i32 @llvm.smax.i32(i32, i32)
declare i32 @llvm.umin.i32(i32, i32)
