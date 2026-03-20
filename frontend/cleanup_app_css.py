with open("frontend/src/App.css", "r", encoding="utf-8") as f:
    text = f.read()

start_marker = "/* ── Buttons"
end_marker = "/* ═══════════════════════════════════════════════════════════════\n   DIAGNOSTIC MODAL"

if start_marker in text and end_marker in text:
    before = text.split(start_marker)[0]
    after = end_marker + text.split(end_marker)[1]
    with open("frontend/src/App.css", "w", encoding="utf-8") as f:
        f.write(before + after)
    print("App.css cleaned up successfully.")
else:
    print("Markers not found.")
