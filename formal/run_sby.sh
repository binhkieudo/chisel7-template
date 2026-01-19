#!/usr/bin/bash

export NTHREADS=4
export SRC_DIR="$(pwd)/../output"
export TOP_MODULE="MemoryAdapterMsgSync"

# List all *.v and *.sv files in SRC_DIR
FILES=$(ls $SRC_DIR/*.v $SRC_DIR/*.sv 2>/dev/null | xargs -n1 basename)

# Construct the [script] reads
# Always include formal_setup.sv as well
SCRIPT_READS=$(echo "$FILES" | sed 's/^/read -sv /')
SCRIPT_READS="$SCRIPT_READS
read -sv formal_setup.sv"

# Construct the [files] list
FILES_LIST=$(echo "$FILES" | sed 's/^/${SRC_DIR}\//')

# Use a temporary file to rebuild run.sby
# We replace the content between [script] and chformal, and between [files] and the next section [file ...]
awk -v script="$SCRIPT_READS" -v files="$FILES_LIST" -v top="$TOP_MODULE" '
  /^\[script\]/ { print; print script; skip=1; next }
  /^chformal/   { skip=0; print; print "prep -top " top; next }
  /^prep -top/  { next }
  /^\[files\]/  { print; print files; print ""; skip=1; next }
  /^\[file /    { skip=0; print; next }
  !skip         { print }
' run.sby > run.sby.tmp && mv run.sby.tmp run.sby

# To actually run, uncomment the next line
# sby -f -j $NTHREADS run.sby

