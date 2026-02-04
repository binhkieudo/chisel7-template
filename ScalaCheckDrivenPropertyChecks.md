# Using ScalaCheckDrivenPropertyChecks

`ScalaCheckDrivenPropertyChecks` is a trait from **ScalaTest** that integrates **ScalaCheck**, allowing you to write "property-based tests." Instead of testing with a few manually chosen values, you define a **Generator**, and ScalaCheck runs your test hundreds of times with different random inputs to find edge cases.

## 1. Setup

To use it, mix the trait into your ScalaTest class:

```scala
import org.scalatestplus.scalacheck.ScalaCheckDrivenPropertyChecks
import org.scalacheck.Gen

class MySpec extends AnyFlatSpec with ScalaCheckDrivenPropertyChecks {
  // Your tests here
}
```

## 2. Defining Generators (`Gen`)

Generators define the "sample space" for your test data.

| Method | Description | Example |
| :--- | :--- | :--- |
| `Gen.choose(min, max)` | Picks a value from a continuous range. | `Gen.choose(0, 100)` |
| `Gen.oneOf(v1, v2...)` | Picks from a specific set of values. | `Gen.oneOf(1, 2, 4, 8)` |
| `Gen.frequency((w,g)...)` | Picks from generators with specific weights. | `Gen.frequency((9, Gen.const(1)), (1, Gen.const(8)))` |
| `Gen.const(value)` | Always returns the same value. | `Gen.const(64)` |
| `Gen.listOfN(n, gen)` | Creates a list of `n` random items. | `Gen.listOfN(10, Gen.choose(0, 255))` |

## 3. Using `forAll`

The `forAll` method takes one or more generators and a function (your test logic). It extracts the generated value so you can use it.

### Simple Example

```scala
val channelGen = Gen.choose(0, 7)

forAll(channelGen) { channel =>
  // This code runs 100 times, each time with a different channel (0-7)
  println(s"Testing channel: $channel")
  assert(channel >= 0 && channel <= 7)
}
```

### Complex Example (Combining Generators)

You can use `for-yield` to build complex objects or multiple related values:

```scala
val configGen = for {
    numPorts <- Gen.oneOf(1, 2, 4, 8)
    rate     <- Gen.choose(50, 100)
    isShuffle <- Gen.oneOf(true, false)
} yield (numPorts, rate, isShuffle)

forAll(configGen) { case (ports, rate, shuffle) =>
    // Run hardware test with these parameters
}
```

## 4. Why use `forAll`?

1. **Edge Case Discovery**: It automatically tests boundaries (like 0, MaxInt, empty lists).
2. **Shrinking**: If a test fails, ScalaCheck tries to find the *smallest* value that causes the failure.
3. **Randomized Seeds**: Every run uses a different sequence of numbers, covering more ground than static lists.

## 5. Integration with Chisel/Chiseltest

When using `chiseltest`, you can place `forAll` **outside** the `test(DUT)` block to recreate the hardware with different parameters, or **inside** the block to use different stimulus on the same hardware.

**Example (Inside `test`):**

```scala
test(new MyModule) { dut =>
  forAll(Gen.choose(0, 255)) { data =>
    dut.io.in.poke(data.U)
    dut.clock.step()
    // Check results...
  }
}
```
