import sys, re

with open('frontend/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    text = f.read()

imports = """import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import styles from './Dashboard.module.css'
"""
text = text.replace("import { getSessionId } from '../utils/session'", imports + "import { getSessionId } from '../utils/session'")

classes_to_module = [
    'dashboard-layout', 'sidebar', 'sidebar-header', 'sidebar-content-area', 'dataset-name',
    'sidebar-section', 'sidebar-section-label', 'role-breakdown', 'role-row', 'role-label-wrap',
    'role-count', 'col-list', 'col-item', 'col-item-name', 'col-item-nunique', 'dashboard-main',
    'status-bar', 'status-item', 'view-toggle', 'analytics-view', 'results-area', 'query-area-bottom',
    'query-input-row', 'query-input', 'suggestion-section', 'chip-row', 'chip', 'empty-state',
    'empty-state-icon', 'pipeline-progress', 'pipeline-label', 'pipeline-steps', 'cannot-answer',
    'cannot-answer-icon', 'overview-card', 'overview-header', 'overview-title', 'overview-summary',
    'kpi-grid', 'chart-grid', 'action-bar', 'role-dot', 'pipeline-step', 'pipeline-dot',
    'chart-card', 'chart-card-header', 'chart-title', 'chart-meta'
]

for c in classes_to_module:
    camel = re.sub(r'-([a-z])', lambda m: m.group(1).upper(), c)
    text = text.replace(f'className="{c}"', f'className={{styles.{camel}}}')
    text = text.replace(f'className="{c} fade-in"', f'className={{styles.{camel}}}')
    
    # Also replace within template literals if there are multiple classes
    text = text.replace(f'"{c} ', f'{{styles.{camel}}} "')
    text = text.replace(f' {c}"', f' {{styles.{camel}}}"')

    # Specifically for template literals like `${styles.chip}`
    # To keep it simple, we don't do blind `"{c}"` replacement to avoid breaking other strings

with open('frontend/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Transformation complete")
