define noundef i8 @f(i8 noundef zeroext %0, i8 noundef zeroext %1) {
  %3 = call i8 @llvm.umax.i8(i8 %0, i8 %1)
  %4 = call i8 @llvm.umin.i8(i8 %0, i8 %1)
  %5 = udiv i8 %3, %4
  ret i8 %5
}
declare i8 @llvm.umax.i8(i8, i8)
declare i8 @llvm.umin.i8(i8, i8)
