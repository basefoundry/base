from __future__ import annotations

import re

REDACTED = "[REDACTED]"
SECRET_KEY_RE = re.compile(r"(token|password|secret|api[-_]?key|authorization)", re.IGNORECASE)
URL_CREDENTIALS_RE = re.compile(r"(?P<prefix>[a-zA-Z][a-zA-Z0-9+.-]*://)[^/@\s]+@")


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


def is_secret_key(value: str) -> bool:
    return SECRET_KEY_RE.search(value) is not None


def redact_text_value(value: str) -> str:
    return URL_CREDENTIALS_RE.sub(lambda match: f"{match.group('prefix')}{REDACTED}@", value)
