#! /usr/bin/python3
# -*- coding: utf8 -*-

# SPDX-FileCopyrightText: 2021 UdS AES <https://www.uni-saarland.de/lehrstuhl/frey.html>
# SPDX-License-Identifier: MIT


import sys

if __name__ == "__main__":
    from worker.__init__ import main

    sys.exit(main())
