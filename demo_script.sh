#!/usr/bin/env bash
# Demo script for attic — recorded by asciinema

BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

type_cmd() {
    echo -en "${BOLD}\$ ${RESET}"
    local cmd="$1"
    for (( i=0; i<${#cmd}; i++ )); do
        echo -n "${cmd:$i:1}"
        sleep 0.045
    done
    echo
    sleep 0.3
    eval "$cmd"
}

cd ~/attic

sleep 0.5
type_cmd "python3.11 attic.py index ~/attic_demo --reset"
sleep 1.5

type_cmd "python3.11 attic.py search \"vector search engine\""
sleep 1.5

type_cmd "python3.11 attic.py search \"async Python\""
sleep 1
