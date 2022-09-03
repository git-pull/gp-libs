#!/usr/bin/env python
import typing as t


def run(*args: object, **kwargs: t.Any) -> t.Optional[str]:
    if args:
        return "Hello"
    return None


if __name__ == "__main__":
    run()
