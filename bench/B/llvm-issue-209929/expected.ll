define range(i32 -1073741824, 1073741824) i32 @f(i32 noundef %0) {
  %2 = mul nsw i32 %0, 3
  %3 = lshr i32 %0, 31
  %4 = add nsw i32 %2, %3
  %5 = ashr i32 %4, 1
  ret i32 %5
}
