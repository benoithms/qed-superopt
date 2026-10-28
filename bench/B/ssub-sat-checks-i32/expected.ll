define i32 @f(i32 noundef %0, i32 noundef %1) {
  %3 = call i32 @llvm.ssub.sat.i32(i32 %0, i32 %1)
  ret i32 %3
}
declare i32 @llvm.ssub.sat.i32(i32, i32)
