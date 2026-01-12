// See README.md for license details.

package gcd

import chisel3._
import chisel3.experimental.BundleLiterals._
import chisel3.simulator.scalatest.ChiselSim
import org.scalatest.freespec.AnyFreeSpec
import org.scalatest.matchers.must.Matchers

import svsim._
import svsim.verilator.Backend._
import svsim.verilator.Backend.CompilationSettings._

class GCDSpec extends AnyFreeSpec with Matchers with ChiselSim {

  implicit val customVerilatorSettings: BackendSettingsModifications = (currentSettings: svsim.Backend.Settings) => {
    currentSettings match {
      case currentSettings: CompilationSettings =>
        val modifiedVerilatorSettings = currentSettings.copy(
          //traceStyle = Some(CompilationSettings.TraceStyle(kind = TraceKind.Vcd, traceUnderscore = false))
          traceStyle = Some(CompilationSettings.TraceStyle(kind = TraceKind.Fst(traceThreads = Some(16)), traceUnderscore = false))
        )
    modifiedVerilatorSettings
      case otherSettings => otherSettings
    }
  }

  "Gcd should calculate proper greatest common denominator" in {
    simulate(new DecoupledGcd(16)) { dut =>
      enableWaves()

      val testValues = for { x <- 0 to 10; y <- 0 to 10} yield (x, y)
      val inputSeq = testValues.map { case (x, y) => (new GcdInputBundle(16)).Lit(_.value1 -> x.U, _.value2 -> y.U) }
      val resultSeq = testValues.map { case (x, y) =>
        (new GcdOutputBundle(16)).Lit(_.value1 -> x.U, _.value2 -> y.U, _.gcd -> BigInt(x).gcd(BigInt(y)).U)
      }

      dut.reset.poke(true.B)
      dut.clock.step()
      dut.reset.poke(false.B)
      dut.clock.step()

      var sent, received, cycles: Int = 0
      while (sent != 100 && received != 100) {
        assert(cycles <= 1000, "timeout reached")

        if (sent < 100) {
          dut.input.valid.poke(true.B)
          dut.input.bits.value1.poke(testValues(sent)._1.U)
          dut.input.bits.value2.poke(testValues(sent)._2.U)
          if (dut.input.ready.peek().litToBoolean) {
            sent += 1
          }
        }

        if (received < 100) {
          dut.output.ready.poke(true.B)
          if (dut.output.valid.peekValue().asBigInt == 1) {
            dut.output.bits.gcd.expect(BigInt(testValues(received)._1).gcd(testValues(received)._2))
            received += 1
          }
        }

        // Step the simulation forward.
        dut.clock.step()
        cycles += 1
      }
    }
  }
}
