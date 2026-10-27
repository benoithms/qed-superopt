define range(i32 0, 64) i32 @f(i64 noundef %0) {
  %2 = call i64 @llvm.cttz.i64(i64 %0, i1 true)
  %3 = trunc i64 %2 to i32
  %4 = icmp eq i64 %0, 0
  %5 = select i1 %4, i32 32, i32 %3
  ret i32 %5
}
declare i64 @llvm.cttz.i64(i64, i1)
