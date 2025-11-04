import json, os

USERS_FILE = "users.json"

if not os.path.exists(USERS_FILE):
    print("No users.json found — nothing to migrate.")
    exit(0)

with open(USERS_FILE, "r") as f:
    data = json.load(f)

changed = False
for k, v in list(data.items()):
    if isinstance(v, str):
        data[k] = {"name": "", "password": v}
        changed = True

if changed:
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print("Migration complete: converted string-password entries to objects.")
else:
    print("No migration needed (already using object format).")
