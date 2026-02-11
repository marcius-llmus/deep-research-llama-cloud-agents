PATCH_FORMAT_TOOL_INSTRUCTIONS = "Use this tool to edit files by applying patches. This is a FREEFORM tool, so do not wrap the patch in JSON. Your patch language is a stripped-down, file-oriented diff format designed to be easy to parse and safe to apply. You can think of it as a high-level envelope"


PATCH_FORMAT_INSTRUCTIONS = """
*** Begin Patch
[ one or more file sections ]
*** End Patch

Within that envelope, you get a sequence of file operations.
You MUST include a header to specify the action you are taking.
Each operation starts with one of three headers:

*** Add File: <path> - create a new file. Every following line is a + line (the initial contents).
*** Delete File: <path> - remove an existing file. Nothing follows.
*** Update File: <path> - patch an existing file in place (optionally with a rename).

Example patch:

```
 *** Begin Patch
 *** Update File: artifacts/report.md
 @@ -0,0 +1,3 @@
 +# Deep Research Report
 +
 +## Overview
 *** End Patch
```

It is important to remember:

- You must include a header with your intended action (Add/Delete/Update)
- You must prefix new lines with `+` even when creating a new file
"""


def get_patch_format_tool_instructions() -> str:
    return PATCH_FORMAT_TOOL_INSTRUCTIONS


def get_patch_format_instructions() -> str:
    return PATCH_FORMAT_INSTRUCTIONS
