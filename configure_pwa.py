from pathlib import Path

p = Path("docs/config.js")
app_id = input("OneSignal App ID: ").strip()

if not app_id:
    raise SystemExit("App ID cannot be empty.")

p.write_text(
    'window.HAPPI_CONFIG = {\\n'
    f'  oneSignalAppId: "{app_id}"\\n'
    '};\\n',
    encoding="utf-8",
)
print("docs/config.js updated.")
