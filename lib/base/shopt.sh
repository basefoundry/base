#
# shopt.sh: Make it easy to turn shopt options on/off and restore the earlier settings
#           in a clean way, preventing any side effects.
#

#
# associative array to hold state
#
declare -gA _shopt_restore 

#
# shopt set one or more options
#
shopt_set() {
    local opt
    for opt; do
        if ! shopt -q "$opt"; then
            echo "$opt not set, setting it"
            shopt -s "$opt"
            _shopt_restore[$opt]=1
        else
            echo "$opt set already"
        fi
    done
}

#
# shopt unset one or more options
#
shopt_unset() {
    local opt restore_type
    for opt; do
        restore_type=${_shopt_restore[$opt]}
        if shopt -q "$opt"; then
            echo "$opt set, unsetting it"
            shopt -u "$opt"
            _shopt_restore[$opt]=2
        else
            echo "$opt unset already"
        fi
        if [[ $restore_type == 1 ]]; then
            unset _shopt_restore[$opt]
        fi
    done
}

#
# restore one or more shopt options which were changed earlier; if no options passed, restore all
#
shopt_restore() {
    local opt opts restore_type
    if (($# > 0)); then
        opts=("$@")
    else
        opts=("${!_shopt_restore[@]}")
    fi
    for opt in "${opts[@]}"; do
        restore_type=${_shopt_restore[$opt]}
        case $restore_type in
        1)
            echo "unsetting $opt"
            shopt -u "$opt"
            unset _shopt_restore[$opt]
            ;;
        2)
            echo "setting $opt"
            shopt -s "$opt"
            unset _shopt_restore[$opt]
            ;;
        *)
            echo "$opt wasn't changed earlier"
            ;;
        esac
    done
}

#
# shop what options set or unset currently
#
shopt_show() {
    local opt restore_type
    for opt in "${!_shopt_restore[@]}"; do 
        restore_type=${_shopt_restore[$opt]}
        if [[ $restore_type == 1 ]]; then
            echo "$opt set"
        elif [[ $restore_type == 2 ]]; then
            echo "$opt unset"
        else
            echo "$opt - unknown status '$restore_type'"
        fi
    done
}
