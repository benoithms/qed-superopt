define range(i32 4, 65) i32 @f(i8 noundef zeroext %0) {
  %2 = and i8 %0, 120
  %3 = or disjoint i8 %2, -128
  %4 = call i8 @llvm.cttz.i8(i8 %3, i1 true)
  %5 = zext nneg i8 %4 to i32
  %6 = lshr i32 512, %5
  ret i32 %6
}
declare i8 @llvm.cttz.i8(i8, i1)
