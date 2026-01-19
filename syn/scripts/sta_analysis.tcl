# OpenSTA Timing and Power Analysis Script
# This script performs STA on the synthesized netlist

# Read liberty file for the target corner
set liberty_file $::env(LIBERTY_FILE)
read_liberty $liberty_file

# Read synthesized netlist
set netlist_file $::env(NETLIST_FILE)
read_verilog $netlist_file

# Link design
set top_module $::env(TOP_MODULE)
link_design $top_module

# Read SDC constraints
set sdc_file $::env(SDC_FILE)
if {[file exists $sdc_file]} {
    read_sdc $sdc_file
} else {
    puts "Warning: SDC file not found: $sdc_file"
}

# Report timing
puts "\n=========================================="
puts "Timing Analysis"
puts "=========================================="

# Check timing
report_checks -path_delay max -format full_clock -fields {slew cap input nets fanout} -digits 3

# Report worst negative slack
puts "\nWorst Negative Slack (Setup):"
report_worst_slack -max

puts "\nWorst Negative Slack (Hold):"
report_worst_slack -min

# Report TNS (Total Negative Slack)
puts "\nTotal Negative Slack:"
report_tns

# Get clock period and calculate max frequency
set clocks [all_clocks]
if {[llength $clocks] > 0} {
    foreach clk $clocks {
        set period [get_property $clk period]
        set wns [sta::worst_slack_cmd "max"]
        
        puts "\nClock: [get_name $clk]"
        puts "  Period: $period ns"
        
        if {$wns != "INF" && $wns != ""} {
            set slack $wns
            set achieved_period [expr {$period - $slack}]
            if {$achieved_period > 0} {
                set max_freq [expr {1000.0 / $achieved_period}]
                puts "  WNS: $slack ns"
                puts "  Achieved Period: $achieved_period ns"
                puts "  Max Frequency: $max_freq MHz"
            }
        } else {
            set max_freq [expr {1000.0 / $period}]
            puts "  Target Frequency: $max_freq MHz"
            puts "  Status: All paths meet timing"
        }
    }
}

# Report power
puts "\n=========================================="
puts "Power Analysis"
puts "=========================================="

# Note: set_switching_activity is not available in all OpenSTA versions
# Using default activity model

report_power

# Write detailed reports to files
set report_dir $::env(REPORT_DIR)

# Report high fanout nets
puts "\n=========================================="
puts "High Fanout Net Report"
puts "=========================================="
# Set a low threshold to catch high fanout nets for reporting
set_max_fanout 20 [current_design]
report_check_types -max_fanout -violators > "$report_dir/${top_module}_sta_fanout.rpt"
# Also report nets with fanout > 10 for more detail if needed
puts "High fanout report generated: $report_dir/${top_module}_sta_fanout.rpt"

# Write timing report
puts "\nWriting timing report..."
report_checks -path_delay max -format full_clock -digits 3 > "$report_dir/${top_module}_sta_timing.rpt"
report_worst_slack >> "$report_dir/${top_module}_sta_timing.rpt"  
report_tns >> "$report_dir/${top_module}_sta_timing.rpt"

# Write power report
puts "Writing power report..."
report_power > "$report_dir/${top_module}_sta_power.rpt"

puts "\n=========================================="
puts "Reports written to:"
puts "  Timing: $report_dir/${top_module}_sta_timing.rpt"
puts "  Power:  $report_dir/${top_module}_sta_power.rpt"
puts "=========================================="

exit
