from typing import Generator
import re


def remove_comments(text: str, comment_style: str = ";") -> str:
    # Remove single-line comments
    text = re.sub(rf"{comment_style}.*", "", text)
    # Remove multi-line comments
    # text = re.sub(r"\(\*[\s\S]*?\*\)", "", text)
    return text


def until_next_closing_parenthesis(s: str) -> tuple[str, str]:
    """
    This function finds the next closing parenthesis in a string and returns the substring up to that point
    and the remaining string.
    """
    if s[0] != "(":
        raise ValueError("The string must start with an opening parenthesis")
    n_closing_parenthesis_to_skip = 0
    for next_parenthesis in re.finditer(r"[\(\)]", s[1:]):
        if next_parenthesis.group() == "(":
            n_closing_parenthesis_to_skip += 1
        elif next_parenthesis.group() == ")":
            if n_closing_parenthesis_to_skip == 0:
                before_closing = s[: next_parenthesis.end() + 1]
                after_closing = s[next_parenthesis.end() + 1 :]
                return before_closing, after_closing
            else:
                n_closing_parenthesis_to_skip -= 1
    raise ValueError("No closing parenthesis found in the string `%s`" % s)


def parentheses_groups(s: str) -> Generator[str, None, None]:
    assert s[0] == "(" and s[-1] == ")", "The string must start and end with parentheses"
    while s != "":
        next_group, s = until_next_closing_parenthesis(s.strip())
        yield next_group
