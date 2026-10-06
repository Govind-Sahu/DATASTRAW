---
name: Legacy package installer issue
description: Replit language-package installs may fail in this Python 3.10 template when its bundled Poetry CLI cannot import poetry.console.main.
---

When adding Python dependencies in this template, first verify the package-management toolchain works. The Replit install callback invoked `poetry add` but failed with an ImportError for `poetry.console.main`; a standard-library implementation avoided making the runnable app depend on a broken installer.

**Why:** the initial project is an older Poetry-based Python template, and the failure occurs before package resolution or installation.

**How to apply:** if the same installer error appears, do not repeat the identical install attempt. Prefer existing packages or the standard library, or repair the package toolchain through supported package management before adding dependencies.
