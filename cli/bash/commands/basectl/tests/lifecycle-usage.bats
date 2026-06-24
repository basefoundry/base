#!/usr/bin/env bats

load ./setup_helpers.bash


@test "basectl setup usage errors return exit code 2" {
    run_base_command setup --badopt

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unknown option '--badopt'."* ]]
    [[ "$output" == *"Run 'basectl setup --help' for usage."* ]]
    [[ "$output" != *"Usage:"* ]]
}

@test "basectl check usage errors return exit code 2" {
    run_base_command check --badopt

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unknown option '--badopt'."* ]]
    [[ "$output" == *"Run 'basectl check --help' for usage."* ]]
    [[ "$output" != *"Usage:"* ]]
}

@test "basectl doctor usage errors return exit code 2" {
    run_base_command doctor --badopt

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unknown option '--badopt'."* ]]
    [[ "$output" == *"Run 'basectl doctor --help' for usage."* ]]
    [[ "$output" != *"Usage:"* ]]
}

@test "basectl onboard usage errors return exit code 2" {
    run_base_command onboard --badopt

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unknown option '--badopt'."* ]]
    [[ "$output" == *"Run 'basectl onboard --help' for usage."* ]]
    [[ "$output" != *"Usage:"* ]]
}

@test "basectl update-profile usage errors return exit code 2" {
    run_base_command update-profile --badopt

    [ "$status" -eq 2 ]
    [[ "$output" == *"Unknown option '--badopt'."* ]]
    [[ "$output" == *"Run 'basectl update-profile --help' for usage."* ]]
    [[ "$output" != *"Usage:"* ]]
}
