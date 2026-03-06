#!/usr/bin/env python3
"""Split large git hunks into sub-hunks or select specific lines for staging.

Modes:
  --find-subhunks  Detect sub-hunks within a parent hunk using fine diff
  --extract-patch  Extract a single sub-hunk as an applicable patch
  --line-select    Build a partial patch from a line range selection
"""

import argparse
import json
import re
import sys

HUNK_RE = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def parse_hunk_header(line):
    """Parse @@ header, return (old_start, old_count, new_start, new_count)."""
    m = HUNK_RE.match(line)
    if not m:
        return None
    old_start = int(m.group(1))
    old_count = int(m.group(2)) if m.group(2) is not None else 1
    new_start = int(m.group(3))
    new_count = int(m.group(4)) if m.group(4) is not None else 1
    return old_start, old_count, new_start, new_count


def parse_diff_hunks(diff_text, target_file):
    """Parse a unified diff and return hunks for target_file.

    Returns list of dicts with keys:
      old_start, old_count, new_start, new_count, header, body
    """
    hunks = []
    in_target = False
    current_hunk = None

    for line in diff_text.splitlines(True):
        if line.startswith('diff --git '):
            # Flush previous hunk
            if current_hunk is not None:
                hunks.append(current_hunk)
                current_hunk = None

            # Check if this diff block is for our target file
            # diff --git a/FILE b/FILE
            parts = line.strip().split(' ')
            if len(parts) >= 4:
                b_path = parts[-1]
                if b_path.startswith('b/'):
                    b_path = b_path[2:]
                in_target = (b_path == target_file)
            else:
                in_target = False
            continue

        if not in_target:
            continue

        if line.startswith('--- ') or line.startswith('+++ '):
            continue

        parsed = parse_hunk_header(line)
        if parsed:
            if current_hunk is not None:
                hunks.append(current_hunk)
            old_start, old_count, new_start, new_count = parsed
            current_hunk = {
                'old_start': old_start,
                'old_count': old_count,
                'new_start': new_start,
                'new_count': new_count,
                'header': line.rstrip('\n'),
                'body': [],
            }
            continue

        if current_hunk is not None:
            # Hunk body lines: context, +, -, or \ No newline
            if line and line[0] in (' ', '+', '-', '\\'):
                current_hunk['body'].append(line.rstrip('\n'))

    if current_hunk is not None:
        hunks.append(current_hunk)

    return hunks


def hunk_preview(body):
    """First + line (or first - line) truncated to 120 chars."""
    for line in body:
        if line.startswith('+'):
            return line[:120]
    for line in body:
        if line.startswith('-'):
            return line[:120]
    return ''


def hunk_in_parent(hunk, parent_old_start, parent_old_count):
    """Check if a fine hunk falls within the parent's old line range."""
    h_old_start = hunk['old_start']
    h_old_count = hunk['old_count']

    if parent_old_count == 0:
        # Parent is a pure addition - can't do old-range containment
        return False

    if h_old_count == 0:
        # Fine hunk is a pure addition - check new range overlap with parent
        # Pure additions have old_start pointing at the line after which insertion
        # happens, so check if that anchor falls within parent's old range
        return (h_old_start >= parent_old_start and
                h_old_start <= parent_old_start + parent_old_count - 1)

    h_end = h_old_start + h_old_count - 1
    p_end = parent_old_start + parent_old_count - 1
    return h_old_start >= parent_old_start and h_end <= p_end


def count_changes(body):
    """Count added and removed lines in a hunk body."""
    added = sum(1 for ln in body if ln.startswith('+'))
    removed = sum(1 for ln in body if ln.startswith('-'))
    return added, removed


def make_patch_header(file_path):
    """Build the diff --git / --- / +++ header lines."""
    return (
        f'diff --git a/{file_path} b/{file_path}\n'
        f'--- a/{file_path}\n'
        f'+++ b/{file_path}\n'
    )


def make_hunk_patch(file_path, hunk):
    """Build a complete patch string for a single hunk."""
    lines = [make_patch_header(file_path)]
    lines.append(f'@@ -{hunk["old_start"]},{hunk["old_count"]} '
                 f'+{hunk["new_start"]},{hunk["new_count"]} @@\n')
    for body_line in hunk['body']:
        lines.append(body_line + '\n')
    return ''.join(lines)


# ---------------------------------------------------------------------------
# Mode: --find-subhunks
# ---------------------------------------------------------------------------

def cmd_find_subhunks(args):
    stdin = sys.stdin.read()
    parts = stdin.split('\x00')
    if len(parts) < 2:
        print(json.dumps({'error': 'expected two sections separated by null byte'}),
              file=sys.stderr)
        sys.exit(1)

    fine_diff = parts[1]
    fine_hunks = parse_diff_hunks(fine_diff, args.file)

    parent_old_start = args.old_start
    parent_old_count = args.old_count

    matching = [h for h in fine_hunks
                if hunk_in_parent(h, parent_old_start, parent_old_count)]

    if len(matching) <= 1:
        print(json.dumps({
            'parent': args.parent,
            'splittable': False,
            'reason': 'single_hunk',
            'suggestion': f'use {args.parent}:START-END for line-level selection',
        }))
        return

    for i, h in enumerate(matching, 1):
        added, removed = count_changes(h['body'])
        print(json.dumps({
            'id': f'{args.parent}.{i}',
            'parent': args.parent,
            'file': args.file,
            'old_start': h['old_start'],
            'old_count': h['old_count'],
            'new_start': h['new_start'],
            'new_count': h['new_count'],
            'added': added,
            'removed': removed,
            'preview': hunk_preview(h['body']),
        }))

    print(json.dumps({
        'summary': True,
        'parent': args.parent,
        'splittable': True,
        'sub_hunks': len(matching),
    }))


# ---------------------------------------------------------------------------
# Mode: --extract-patch
# ---------------------------------------------------------------------------

def cmd_extract_patch(args):
    fine_diff = sys.stdin.read()
    fine_hunks = parse_diff_hunks(fine_diff, args.file)

    matching = [h for h in fine_hunks
                if hunk_in_parent(h, args.parent_old_start, args.parent_old_count)]

    idx = args.sub_index  # 1-based
    if idx < 1 or idx > len(matching):
        print(json.dumps({
            'error': 'sub_hunk_not_found',
            'id': args.id,
            'detail': f'parent {args.id.split(".")[0]} has {len(matching)} sub-hunks',
        }), file=sys.stderr)
        sys.exit(1)

    hunk = matching[idx - 1]
    sys.stdout.write(make_hunk_patch(args.file, hunk))


# ---------------------------------------------------------------------------
# Mode: --line-select
# ---------------------------------------------------------------------------

def cmd_line_select(args):
    normal_diff = sys.stdin.read()
    all_hunks = parse_diff_hunks(normal_diff, args.file)

    hunk_num = args.hunk_num  # 1-based
    if hunk_num < 1 or hunk_num > len(all_hunks):
        print(json.dumps({
            'error': 'hunk_not_found',
            'id': args.id,
            'detail': f'file {args.file} has {len(all_hunks)} hunks',
        }), file=sys.stderr)
        sys.exit(1)

    hunk = all_hunks[hunk_num - 1]
    body = hunk['body']

    # Parse line range
    range_parts = args.lines.split('-')
    start = int(range_parts[0])
    end = int(range_parts[1])

    if start < 1 or end > len(body) or start > end:
        print(json.dumps({
            'error': 'line_range_out_of_bounds',
            'id': args.id,
            'lines': args.lines,
            'max_lines': len(body),
        }), file=sys.stderr)
        sys.exit(1)

    # Check if full hunk selected
    if start == 1 and end == len(body):
        print(json.dumps({
            'note': 'full_hunk_selected',
            'id': args.id,
            'lines': args.lines,
        }), file=sys.stderr)
        sys.stdout.write(make_hunk_patch(args.file, hunk))
        return

    # Build partial patch body
    new_body = []
    has_changes = False

    for i, line in enumerate(body, 1):
        in_range = start <= i <= end

        if line.startswith('+'):
            if in_range:
                new_body.append(line)
                has_changes = True
            # else: drop non-selected additions (they don't exist in the
            # old file and can't appear as context)
        elif line.startswith('-'):
            if in_range:
                new_body.append(line)
                has_changes = True
            else:
                # Non-selected removal becomes context (line exists in old
                # file, git apply needs it for position matching)
                new_body.append(' ' + line[1:])
        else:
            # Context lines and \ No newline - always keep
            new_body.append(line)

    if not has_changes:
        print(json.dumps({
            'error': 'no_changes_in_range',
            'id': args.id,
            'lines': args.lines,
            'detail': 'selected range has no additions or removals',
        }), file=sys.stderr)
        sys.exit(1)

    # Recalculate counts (\ No newline lines don't count)
    old_count = 0
    new_count = 0
    for ln in new_body:
        if ln.startswith(' '):
            old_count += 1
            new_count += 1
        elif ln.startswith('-'):
            old_count += 1
        elif ln.startswith('+'):
            new_count += 1

    patch = make_patch_header(args.file)
    patch += (f'@@ -{hunk["old_start"]},{old_count} '
              f'+{hunk["new_start"]},{new_count} @@\n')
    for line in new_body:
        patch += line + '\n'

    sys.stdout.write(patch)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Split git hunks into sub-hunks')

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--find-subhunks', action='store_true')
    mode_group.add_argument('--extract-patch', action='store_true')
    mode_group.add_argument('--line-select', action='store_true')

    # --find-subhunks args
    parser.add_argument('--parent')
    parser.add_argument('--old-start', type=int)
    parser.add_argument('--old-count', type=int)

    # --extract-patch args
    parser.add_argument('--id')
    parser.add_argument('--parent-old-start', type=int)
    parser.add_argument('--parent-old-count', type=int)
    parser.add_argument('--sub-index', type=int)

    # --line-select args
    parser.add_argument('--hunk-num', type=int)
    parser.add_argument('--lines')

    # Shared
    parser.add_argument('--file')

    args = parser.parse_args()

    if args.find_subhunks:
        for req in ('parent', 'old_start', 'old_count', 'file'):
            if getattr(args, req) is None:
                parser.error(f'--find-subhunks requires --{req.replace("_", "-")}')
        cmd_find_subhunks(args)
    elif args.extract_patch:
        for req in ('id', 'parent_old_start', 'parent_old_count', 'sub_index', 'file'):
            if getattr(args, req) is None:
                parser.error(f'--extract-patch requires --{req.replace("_", "-")}')
        cmd_extract_patch(args)
    elif args.line_select:
        for req in ('id', 'file', 'hunk_num', 'lines'):
            if getattr(args, req) is None:
                parser.error(f'--line-select requires --{req.replace("_", "-")}')
        cmd_line_select(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
