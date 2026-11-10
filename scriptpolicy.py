import fnmatch
import re

# These never run: dos can take targets down, and broadcast reaches hosts outside the scope
BLOCKED_SCRIPTS = {"dos", "broadcast"}
TOKEN_RE = re.compile(r"[(),]|[^\s(),]+")
NAME_RE = re.compile(r"[A-Za-z0-9_.*-]+")


def askConfirmation(message):
  try:
    return input(message + " [y/N] ").strip().lower() in ("y", "yes", "s", "si", "sí")
  except (EOFError, KeyboardInterrupt):
    return False


# Evaluate an NSE --script selector against the known script categories without altering the expression
def analyzeScriptExpression(expression, scripts, template=False):
  tokens = TOKEN_RE.findall(expression)
  if not tokens:
    return {
      "parsed": False,
      "error": "invalid script name: " + expression,
      "blocked": set(),
      "blockedToken": set(),
      "blockedSelected": set(),
      "selected": set(),
      "categories": set(),
      "hasNot": False,
      "unsafe": False,
      "unsafeTerm": False,
      "external": False,
      "needsConfirm": True,
      "folder": False,
    }
  allScripts = set(scripts)
  pos = 0
  hasNot = False
  unsafeTerm = False
  blockedToken = set()
  blockedPositive = set()
  firstError = None
  parseError = None
  folder = False

  # Nmap's NSE parser (nse_main.lua) matches operators, categories, and all/true/false case-insensitively
  def op(token):
    return token.lower() if template else token

  def parseOr(negated):
    nonlocal pos
    left = parseAnd(negated)
    while pos < len(tokens) and op(tokens[pos]) in ("or", ","):
      pos += 1
      left = left | parseAnd(negated)
    return left

  def parseAnd(negated):
    nonlocal pos
    left = parseNot(negated)
    while pos < len(tokens) and op(tokens[pos]) == "and":
      pos += 1
      left = left & parseNot(negated)
    return left

  def parseNot(negated):
    nonlocal pos, hasNot
    if pos < len(tokens) and op(tokens[pos]) == "not":
      pos += 1
      hasNot = True
      return allScripts - parseNot(not negated)
    return parsePrimary(negated)

  def parsePrimary(negated):
    nonlocal pos, unsafeTerm, firstError, parseError, folder
    if pos >= len(tokens):
      if "(" in tokens or ")" in tokens:
        raise ValueError("unbalanced parentheses: " + expression)
      raise ValueError("invalid script name: " + expression)
    token = tokens[pos]
    if token == "(":
      pos += 1
      value = parseOr(negated)
      if pos >= len(tokens) or tokens[pos] != ")":
        raise ValueError("unbalanced parentheses: " + expression)
      pos += 1
      return value
    if token == ")":
      raise ValueError("unbalanced parentheses: " + expression)
    if op(token) in ("and", "or", ",", "not"):
      raise ValueError("invalid script name: " + token)
    # Nmap also loads scripts by file path or by folder, and the file system may ignore case
    if template:
      base = re.split(r"[/\\]", token)[-1]
      isPath = base != token
      if isPath and not base.lower().endswith(".nse"):
        blockedToken.add(token)
        blockedPositive.update(BLOCKED_SCRIPTS)
        folder = True
        raise ValueError("script directory not allowed: " + token)
      stem = re.sub(r"\.nse$", "", base, flags=re.IGNORECASE).lower()
      found = set()
      for script, categories in scripts.items():
        if script.lower() == stem:
          found |= categories & BLOCKED_SCRIPTS
      if found and (isPath or token not in scripts):
        blockedToken.add(token)
        if not negated:
          blockedPositive.update(found)
        if firstError is None:
          firstError = "script not allowed: " + token
        if isPath:
          raise ValueError("script not allowed: " + token)
    if not NAME_RE.fullmatch(token):
      raise ValueError("invalid script name: " + token)
    pos += 1
    name = re.sub(r"\.nse$", "", token)
    lower = token.lower() if template else token
    if template and lower == "false" and scripts:
      return set()
    if template and lower in ("all", "true"):
      matches = dict(scripts)
    else:
      matches = {script: found for script, found in scripts.items() if fnmatch.fnmatchcase(script, name) or lower in found}
    if lower in BLOCKED_SCRIPTS:
      blockedToken.add(lower)
      if not negated:
        blockedPositive.add(lower)
      if firstError is None:
        firstError = "script category not allowed: " + token
      return set(matches)
    if not matches:
      if parseError is None:
        parseError = "unknown script or category: " + token
      if firstError is None:
        firstError = parseError
      return set()
    if name in matches and matches[name] & BLOCKED_SCRIPTS:
      blockedToken.add(token)
      if not negated:
        blockedPositive.update(matches[name] & BLOCKED_SCRIPTS)
      if firstError is None:
        firstError = "script not allowed: " + token
    if any("safe" not in found for found in matches.values()):
      unsafeTerm = True
    return set(matches)

  try:
    selected = parseOr(False)
    if pos < len(tokens):
      if tokens[pos] in ("(", ")") or "(" in tokens or ")" in tokens:
        raise ValueError("unbalanced parentheses: " + expression)
      raise ValueError("invalid script name: " + tokens[pos])
    if parseError is not None:
      raise ValueError(parseError)
  except ValueError as e:
    return {
      "parsed": False,
      "error": firstError or str(e),
      "blocked": set(blockedPositive),
      "blockedToken": blockedToken,
      "blockedSelected": set(blockedPositive),
      "selected": set(),
      "categories": set(),
      "hasNot": hasNot,
      "unsafe": False,
      "unsafeTerm": unsafeTerm,
      "external": False,
      "needsConfirm": True,
      "folder": folder,
    }

  categories = {category for script in selected for category in scripts[script]}
  blockedSelected = (categories & BLOCKED_SCRIPTS) | blockedPositive
  unsafe = any("safe" not in scripts[script] for script in selected)
  external = "external" in categories
  needsConfirm = hasNot or unsafe or external
  return {
    "parsed": True,
    "error": firstError,
    "blocked": blockedSelected,
    "blockedToken": blockedToken,
    "blockedSelected": blockedSelected,
    "selected": selected,
    "categories": categories,
    "hasNot": hasNot,
    "unsafe": unsafe,
    "unsafeTerm": unsafeTerm,
    "external": external,
    "needsConfirm": needsConfirm,
    "folder": folder,
  }
