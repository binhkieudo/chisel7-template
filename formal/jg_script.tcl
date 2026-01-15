
# JasperGold Automation Script for QueueModule

# 1. Configuration
set output_dir "../output"
set top_module "QueueModule"
set rst_cycles 2

# Clear any valid logic from previous runs
clear -all

# 2. Analyze
# We need to set include directories so that `include "layers-..."` works
set inc_options "+define+ASSERT_VERBOSE_COND=1 +define+STOP_COND=1"
append inc_options " +incdir+${output_dir}"
append inc_options " +incdir+${output_dir}/verification"
append inc_options " +incdir+${output_dir}/verification/assert"
append inc_options " +incdir+${output_dir}/verification/assume"
append inc_options " +incdir+${output_dir}/verification/cover"

puts "Info: Analyzing Design Files from filelist.f..."
set fp [open "${output_dir}/filelist.f" r]
set file_data [read $fp]
close $fp

foreach line [split $file_data "\n"] {
    set filename [string trim $line]
    if {$filename != ""} {
        analyze -sv09 {*}$inc_options "${output_dir}/${filename}"
    }
}

puts "Info: Analyzing Verification Layers..."
# Find all layer bind files in the verification directory
# We assume the naming convention "layers-*-{Assert,Assume,Cover}.sv"
# Helper proc to analyze files matching a glob pattern
proc analyze_layers {pattern options} {
    set layer_files [glob -nocomplain $pattern]
    foreach layer_file $layer_files {
        analyze -sv09 {*}$options $layer_file
    }
}

analyze_layers "${output_dir}/verification/assert/layers-*-Assert.sv" $inc_options
analyze_layers "${output_dir}/verification/assume/layers-*-Assume.sv" $inc_options
analyze_layers "${output_dir}/verification/cover/layers-*-Cover.sv" $inc_options

# 3. Elaborate
elaborate -top $top_module

# 4. Clock and Reset
# Adjust these names if your top level ports differ (e.g. clk vs clock)
clock clock

# Configure Reset
# We use a waveform expression to hold reset high for 'rst_cycles'
# Syntax: {signal_name} {value_sequence} -non_resettable_regs {0}
# Example: 1'b1 for N cycles, then 1'b0
reset -expression {reset}

# 5. Proof
puts "Info: Starting Proof..."

# Only check properties that trigger AFTER the reset sequence avoids false failures during initialization
# 'check_assumptions' verifies that our assumptions don't conflict or block everything
check_assumptions

# Prove all properties (Asserts and Covers)
prove -all
