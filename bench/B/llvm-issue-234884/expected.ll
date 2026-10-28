define range(i64 -4294967295, 4294967296) i64 @f(i32 noundef %0, i32 noundef %1) {
  %3 = zext i32 %0 to i64
  %4 = zext i32 %1 to i64
  %5 = sub nsw i64 %3, %4
  %6 = call i64 @llvm.abs.i64(i64 %5, i1 false)
  ret i64 %6
}
declare i64 @llvm.abs.i64(i64, i1)
