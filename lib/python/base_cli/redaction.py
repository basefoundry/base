from __future__ import annotations


REDACTED = "[REDACTED]"


def option_name_to_parameter(param_decl: str) -> str:
    name = param_decl.lstrip("-")
    return name.replace("-", "_")


def parameter_name_from_decls(param_decls: tuple[str, ...]) -> str:
    options = [decl for decl in param_decls if decl.startswith("--")]
    if options:
        return option_name_to_parameter(options[0])
    return option_name_to_parameter(param_decls[0])


def redact_argv(argv: list[str], sensitive_options: set[str]) -> list[str]:
    redacted: list[str] = []
    skip_next = False
    for arg in argv:
        if skip_next:
            redacted.append(REDACTED)
            skip_next = False
            continue

        option, separator, _value = arg.partition("=")
        normalized = option_name_to_parameter(option) if option.startswith("--") else option
        if option.startswith("--") and normalized in sensitive_options:
            if separator:
                redacted.append(f"{option}={REDACTED}")
            else:
                redacted.append(option)
                skip_next = True
            continue

        redacted.append(arg)
    return redacted
