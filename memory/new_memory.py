import json
import os

FACTS_FILE = os.path.join(os.path.dirname(__file__), "facts.json")
COMMANDS_FILE = os.path.join(os.path.dirname(__file__), "commands.json")

def _load(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def _save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ─── FACTS ───────────────────────────────────────────
def save_fact(key, value):
    facts = _load(FACTS_FILE)
    facts[key] = value
    _save(FACTS_FILE, facts)

def get_all_facts():
    return _load(FACTS_FILE)

def forget_fact(key):
    facts = _load(FACTS_FILE)
    facts.pop(key, None)
    _save(FACTS_FILE, facts)

# ─── COMMANDS ────────────────────────────────────────
def save_command(trigger, action):
    commands = _load(COMMANDS_FILE)
    commands[trigger.lower()] = action
    _save(COMMANDS_FILE, commands)

def get_command(trigger):
    commands = _load(COMMANDS_FILE)
    return commands.get(trigger.lower())

def get_all_commands():
    return _load(COMMANDS_FILE)

def forget_command(trigger):
    commands = _load(COMMANDS_FILE)
    commands.pop(trigger.lower(), None)
    _save(COMMANDS_FILE, commands)