import os

def replace_in_file(filepath, replacements):
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    for old, new in replacements:
        text = text.replace(old, new)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

replace_in_file("frontend/src/components/ThemeToggle.jsx", [
    ('import { useState, useEffect } from "react"', 'import { useState, useEffect } from "react"\nimport Button from "./ui/Button"'),
    ('<button\n      className="btn btn-ghost btn-sm btn-icon"', '<Button size="sm" variant="ghost" className="btn-icon"'),
    ('</button>', '</Button>')
])

replace_in_file("frontend/src/components/FullReportWidget.jsx", [
    ("import React,", "import Button from './ui/Button'\nimport React,"),
    ('<button className="btn btn-secondary" onClick={onComplete}>Close</button>', '<Button variant="secondary" onClick={onComplete}>Close</Button>'),
    ('<button className="btn btn-primary btn-sm" onClick={handleExport} disabled={exporting}>', '<Button size="sm" variant="primary" onClick={handleExport} disabled={exporting}>'),
    ('<button className="btn btn-ghost btn-sm" onClick={onComplete}>✕ Close</button>', '<Button size="sm" variant="ghost" onClick={onComplete}>✕ Close</Button>'),
    ('</button>', '</Button>')
])

replace_in_file("frontend/src/components/ExportButton.jsx", [
    ("import { useState } from 'react'", "import { useState } from 'react'\nimport Button from './ui/Button'"),
    ('<button className="btn btn-secondary btn-sm" onClick={handleExport} disabled={exporting}>', '<Button variant="secondary" size="sm" onClick={handleExport} disabled={exporting}>'),
    ('</button>', '</Button>')
])

replace_in_file("frontend/src/components/ChatBot.jsx", [
    ("import { useState, useRef, useEffect } from 'react'", "import { useState, useRef, useEffect } from 'react'\nimport Button from './ui/Button'"),
    ('<button className="btn btn-primary chatbot-send-btn"', '<Button variant="primary" className="chatbot-send-btn"'),
    ('          ↑\n        </button>', '          ↑\n        </Button>')
])

print("Widget migration complete")
