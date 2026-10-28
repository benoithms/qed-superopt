define zeroext i1 @f(i32 noundef %0, i32 noundef %1) {
  %3 = call { i32, i1 } @llvm.sadd.with.overflow.i32(i32 %0, i32 %1)
  %4 = extractvalue { i32, i1 } %3, 1
  ret i1 %4
}
declare { i32, i1 } @llvm.sadd.with.overflow.i32(i32, i32)
