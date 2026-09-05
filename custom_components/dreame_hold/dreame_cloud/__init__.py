"""Minimal, device-agnostic Dreame/MOVA cloud client.

Extracted and genericized from the cloud transport layer of two MIT-licensed
projects (see NOTICE at the repo root for full attribution):

- https://github.com/Tasshack/dreame-vacuum
- https://github.com/antondaubert/dreame-mower

Only the login / device-list / get_properties plumbing is kept; nothing here
assumes a specific device category (vacuum, mower, handheld, ...), which is
exactly what makes it usable to probe a Dreame H14.
"""
