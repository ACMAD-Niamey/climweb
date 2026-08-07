#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "climweb.config.settings.dev")

    # Django's test runner discovers tests from the current working directory
    # when no labels are given. Run from the src/ layout root (one level above
    # the "climweb" package) so discovery lands on "climweb.*" dotted paths
    # instead of stalling on the non-package "src" directory above it.
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(src_dir)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
