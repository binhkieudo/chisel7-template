#!/bin/bash
# Wrapper script to run JasperGold with the generated tcl script

# Check if jg is in path (optional)
if ! command -v jg &> /dev/null; then
    echo "Warning: 'jg' command not found in PATH. Make sure JasperGold environment is sourced."
    echo "Attempting to run anyway..."
fi

jg -no_gui -tcl jg_script.tcl
