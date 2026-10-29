define range(i32 1, 11) i32 @f(i64 noundef %0) {
  %t1 = or i64 %0, 1
  %t2 = call i64 @llvm.ctlz.i64(i64 %t1, i1 true)
  %t3 = xor i64 %t2, 63
  %t4 = trunc i64 %t3 to i32
  %t5 = mul i32 %t4, 9
  %t6 = add i32 %t5, 73
  %t7 = lshr i32 %t6, 6
  ret i32 %t7
}
declare i64 @llvm.ctlz.i64(i64, i1)
