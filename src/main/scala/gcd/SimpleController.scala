// See README.md for license details.

package gcd

import chisel3._
import chisel3.util._
import _root_.circt.stage.ChiselStage

class QueueModule extends Module {
  val io = IO(new Bundle {
    val in  = Flipped(Decoupled(UInt(8.W)))
    val out = Decoupled(UInt(8.W))
  })

  // This instantiates a 4-entry 8-bit FIFO
  io.out <> Queue(io.in, entries = 4)

  assert(!(!io.in.ready && !io.out.valid), "Unexpected state")
  cover(io.out.fire, "cover_out_fire")
}

/**
 * Generate Verilog sources and save it in file GCD.v
 */
object QueueModule extends App {
  ChiselStage.emitSystemVerilogFile(
    new QueueModule,
    Array("--target-dir", "output"),
    firtoolOpts = Array(
      "-disable-all-randomization", 
      "-strip-debug-info",
      //"--verification-flavor=sva", // Uncomment when using with Jasper
      "--lowering-options=disallowLocalVariables")
  )
}
