#!/usr/bin/env python3
"""Search and read claude.ai chats from the official data export.

Get the export: claude.ai -> Settings -> Privacy -> Export data. Unzip the
emailed archive and point this tool at its conversations.json.

  claude_chats.py conversations.json list [--limit N]
  claude_chats.py conversations.json search "text" [--limit N]
  claude_chats.py conversations.json show <uuid-prefix> [--out FILE.md]
"""
import argparse
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def msg_text(m):
    if m.get("text"):
        return m["text"]
    parts = [c.get("text", "") for c in m.get("content", []) if c.get("type") == "text"]
    return "\n".join(p for p in parts if p)


def render(conv):
    out = [f"# {conv.get('name') or '(untitled)'}",
           f"_{conv.get('uuid')} · created {conv.get('created_at', '?')}_", ""]
    for m in conv.get("chat_messages", []):
        who = "You" if m.get("sender") == "human" else "Claude"
        out += [f"**{who}** ({m.get('created_at', '')})", "", msg_text(m), ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--limit", type=int, default=50)
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("show"); p.add_argument("uuid"); p.add_argument("--out")
    a = ap.parse_args()

    convs = sorted(load(a.file), key=lambda c: c.get("updated_at", ""), reverse=True)

    if a.cmd == "list":
        for c in convs[: a.limit]:
            print(f"{c['uuid'][:8]}  {c.get('updated_at', '')[:10]}  {c.get('name') or '(untitled)'}")
    elif a.cmd == "search":
        q, n = a.query.lower(), 0
        for c in convs:
            for m in c.get("chat_messages", []):
                t = msg_text(m)
                i = t.lower().find(q)
                if i >= 0:
                    snip = t[max(0, i - 60): i + 100].replace("\n", " ")
                    print(f"{c['uuid'][:8]}  {c.get('name') or '(untitled)'}\n    …{snip}…")
                    n += 1
                    break
            if n >= a.limit:
                break
    else:
        hits = [c for c in convs if c["uuid"].startswith(a.uuid)]
        if len(hits) != 1:
            sys.exit(f"{len(hits)} conversations match '{a.uuid}'")
        text = render(hits[0])
        if a.out:
            open(a.out, "w", encoding="utf-8").write(text)
        else:
            print(text)


if __name__ == "__main__":
    main()
