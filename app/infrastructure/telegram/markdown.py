import re

MARKDOWN_SPECIAL_PATTERN = re.compile(r"([\\`*_{}\[\]<>()#+\-.!~])")


def escape_markdown(value: str) -> str:
    return MARKDOWN_SPECIAL_PATTERN.sub(r"\\\1", value.replace("\n", " "))


def escape_table_cell(value: str) -> str:
    return escape_markdown(value).replace("|", r"\|")
