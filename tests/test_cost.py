from qed.cost import asm_instructions, cost, ir_instructions
from qed.extract import function, splice

# srem(x, 250) != x, and the range check LLVM misses (issue 215060).
SRC = """define i1 @f(i64 %0) {
  %2 = srem i64 %0, 250
  %3 = icmp ne i64 %2, %0
  ret i1 %3
}
"""
TGT = splice(SRC, "  %2 = add i64 %0, -250\n  %3 = icmp ult i64 %2, -499\n  ret i1 %3")


def test_cost_reads_llc_and_mca():
    c = cost(SRC)
    assert c.ir_insts == 3
    assert c.asm_insts == len(asm_instructions(c.asm)) > 3
    assert c.mca_cycles > 0
    assert "retq" in c.asm


def test_better_rewrite_is_cheaper():
    src, tgt = cost(SRC), cost(TGT)
    assert tgt.asm_insts < src.asm_insts
    assert tgt.mca_cycles < src.mca_cycles


def test_ir_instructions_skip_labels_and_comments():
    fn = function("define i32 @f(i32 %0) {\nentry:\n  ; comment\n  ret i32 %0 ; tail\n}\n")
    assert ir_instructions(fn) == 1


def test_asm_instructions_skip_directives():
    asm = "f:\n\t.cfi_startproc\n# %bb.0:\n\tmovl\t%edi, %eax # copy\n\tretq\n.Lfunc_end0:"
    assert asm_instructions(asm) == ["movl\t%edi, %eax", "retq"]
